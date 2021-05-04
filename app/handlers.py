from datetime import timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.app_utils import get_password_hash
from app.authentication import authenticate_user, create_access_token, get_current_user
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.connection_manager import manager
from app.db_models import Bot, RoleEnum, User
from app.db_utils import get_session, get_user
from app.pydantic_models import (
    AddBotCommandResponse,
    AddBotModel,
    AddBotResponse,
    CommandModel,
    DeleteBotCommandResponse,
    EditBotCommandModel,
    EditBotCommandResponse,
    GetBotCommandsResponse,
    GetBotsResponse,
    GetHistoryResponse,
    RegisterModel,
    RegisterResponse,
    Token,
    UserIdModel,
)
from app.redis_utils import CommandDoesNotExistError, CommandExistsError, redis_dao


async def login_for_access_token(
    session: Session = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.username}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type='bearer')


async def read_users_me(current_user: User = Depends(get_current_user)) -> UserIdModel:
    return UserIdModel(user_id=current_user.id, role=current_user.role)


async def register(
    data: RegisterModel, session: Session = Depends(get_session)
) -> RegisterResponse:
    if get_user(session, data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Couldn't register user",
        )

    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role=RoleEnum.USER,
    )

    try:
        session.add(user)
        session.commit()
    except IntegrityError as e:
        if get_user(session, data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Couldn't register user",
            ) from e

    return RegisterResponse(registered_username=user.username)


async def get_bots(
    _: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> GetBotsResponse:
    bots = session.query(Bot).all()

    result = []
    for bot in bots:
        result.append(
            {
                'bot_id': bot.id,
                'bot_name': bot.name,
                'author_username': bot.author.username,
            }
        )

    return GetBotsResponse(bots=result)


async def add_bot(
    bot_model: AddBotModel,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AddBotResponse:
    verify_role_admin(current_user)

    bot = Bot(name=bot_model.name, author_id=current_user.id)
    session.add(bot)
    session.commit()

    await redis_dao.add_bot_commands_list(bot.id, bot_model.commands)

    return AddBotResponse(bot_id=bot.id, name=bot.name, author=bot.author.username)


async def get_bot_commands(
    bot_id: int,
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GetBotCommandsResponse:
    bot = session.query(Bot).get(bot_id)
    commands = await redis_dao.get_bot_commands(bot_id)

    return GetBotCommandsResponse(bot_name=bot.name, commands=commands)


async def add_bot_command(
    bot_id: int,
    command_model: CommandModel,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AddBotCommandResponse:
    verify_role_admin(current_user)

    bot = session.query(Bot).get(bot_id)

    try:
        await redis_dao.add_bot_command(bot_id, command_model)
    except CommandExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Command already exists',
        ) from e

    return AddBotCommandResponse(
        bot_name=bot.name,
        added_command=command_model.dict(),
        author_username=current_user.username,
    )


async def edit_bot_command(
    bot_id: int,
    command_id: int,
    model: EditBotCommandModel,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> EditBotCommandResponse:
    verify_role_admin(current_user)

    bot = session.query(Bot).get(bot_id)

    try:
        await redis_dao.edit_bot_command(bot_id, command_id, model.new_response)
    except CommandDoesNotExistError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Command does not exist',
        ) from e

    bot_command = await redis_dao.get_bot_command(bot_id, command_id)
    assert bot_command is not None

    command, new_response = bot_command

    return EditBotCommandResponse(
        bot_name=bot.name, command=command, new_response=new_response
    )


async def delete_bot_command(
    bot_id: int,
    command_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DeleteBotCommandResponse:
    verify_role_admin(current_user)

    bot = session.query(Bot).get(bot_id)

    try:
        await redis_dao.delete_bot_command(bot_id, command_id)
    except CommandDoesNotExistError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Command does not exist',
        ) from e

    return DeleteBotCommandResponse(bot_name=bot.name, deleted_command_id=command_id)


async def get_messages(
    bot_id: int, user_id: int, current_user: User = Depends(get_current_user)
) -> GetHistoryResponse:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Permission denied',
        )

    history = await redis_dao.get_history_from_redis(user_id, bot_id)
    return GetHistoryResponse(history=history)


async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    if current_user.id != user_id:
        return

    await manager.connect(websocket)
    user_full_name = current_user.full_name
    bot_name = session.query(Bot).get(bot_id).name

    try:
        await redis_dao.create_reader_task(manager, user_id, bot_id)
        while True:
            message = await websocket.receive_text()
            await redis_dao.publish_to_redis(user_id, bot_id, user_full_name, message)
            bot_response = await redis_dao.get_bot_response_by_message(bot_id, message)
            if bot_response:
                await redis_dao.publish_to_redis(
                    user_id, bot_id, bot_name, bot_response
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.broadcast(f'{user_full_name} left')


async def on_startup() -> None:
    await redis_dao.init_conn()


async def on_shutdown() -> None:
    await redis_dao.close_redis_connection()


def verify_role_admin(current_user: User) -> None:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Permission denied',
        )
