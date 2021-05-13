from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from starlette import status

from app.authentication import get_current_user, verify_role_admin
from app.db_models import Bot, Command, User
from app.db_utils import get_session
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
)

router = APIRouter()


@router.get('/bots')
def get_bots(
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


@router.post('/bots')
def add_bot(
    bot_model: AddBotModel,
    current_user: User = Depends(verify_role_admin),
    session: Session = Depends(get_session),
) -> AddBotResponse:

    bot = Bot(name=bot_model.name, author_id=current_user.id)
    session.add(bot)
    session.commit()

    # await redis_dao.add_bot_commands_list(bot.id, bot_model.commands)
    for command in bot_model.commands:
        new_command = Command(
            message=command.command, response=command.response, bot_id=bot.id
        )
        session.add(new_command)

    session.commit()

    return AddBotResponse(bot_id=bot.id, name=bot.name, author=bot.author.username)


@router.get('/bots/{bot_id}/commands')
def get_bot_commands(
    bot_id: int,
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GetBotCommandsResponse:
    bot = session.query(Bot).get(bot_id)
    commands = session.query(Command).filter_by(bot_id=bot_id).all()
    # commands = await redis_dao.get_bot_commands(bot_id)
    result = []
    for command in commands:
        result.append(
            {
                'command_id': command.id,
                'command': command.message,
                'response': command.response,
            }
        )

    return GetBotCommandsResponse(bot_name=bot.name, commands=result)


@router.post('/bots/{bot_id}/commands')
def add_bot_command(
    bot_id: int,
    command_model: CommandModel,
    current_user: User = Depends(verify_role_admin),
    session: Session = Depends(get_session),
) -> AddBotCommandResponse:
    bot = session.query(Bot).get(bot_id)

    try:
        command = Command(
            message=command_model.command,
            response=command_model.response,
            bot_id=bot_id,
        )
        session.add(command)
        session.commit()
        # await redis_dao.add_bot_command(bot_id, command_model)
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Command already exists',
        ) from e

    return AddBotCommandResponse(
        bot_name=bot.name,
        added_command=command_model.dict(),
        author_username=current_user.username,
    )


@router.patch('/bots/{bot_id}/commands/{command_id}')
def edit_bot_command(
    bot_id: int,
    command_id: int,
    model: EditBotCommandModel,
    _: User = Depends(verify_role_admin),
    session: Session = Depends(get_session),
) -> EditBotCommandResponse:
    bot = session.query(Bot).get(bot_id)

    try:
        # await redis_dao.edit_bot_command(bot_id, command_id, model.new_response)
        command = session.query(Command).filter_by(id=command_id).one()
        command.response = model.new_response
        session.commit()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Command does not exist',
        ) from e

    return EditBotCommandResponse(
        bot_name=bot.name, command=command.message, new_response=command.response
    )


@router.delete('/bots/{bot_id}/commands/{command_id}')
def delete_bot_command(
    bot_id: int,
    command_id: int,
    _: User = Depends(verify_role_admin),
    session: Session = Depends(get_session),
) -> DeleteBotCommandResponse:
    bot = session.query(Bot).get(bot_id)

    try:
        command = session.query(Command).filter_by(id=command_id).one()
        session.delete(command)
        session.commit()
        # await redis_dao.delete_bot_command(bot_id, command_id)
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Command does not exist',
        ) from e

    return DeleteBotCommandResponse(bot_name=bot.name, deleted_command_id=command_id)
