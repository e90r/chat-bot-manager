import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.authentication import get_current_user
from app.connection_manager import manager
from app.db_models import Bot, Command, RoleEnum, User
from app.db_utils import get_session
from app.pydantic_models import GetHistoryResponse
from app.redis_utils import redis_dao

router = APIRouter()


@router.get('/bots/{bot_id}/messages/{user_id}')
async def get_messages(
    bot_id: int, user_id: int, current_user: User = Depends(get_current_user)
) -> GetHistoryResponse:
    if current_user.id != user_id or current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Permission denied',
        )

    history = await redis_dao.get_history_from_redis(user_id, bot_id)
    return GetHistoryResponse(history=history)


@router.websocket('/ws/{bot_id}')
async def websocket_endpoint(
    websocket: WebSocket,
    bot_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    await manager.connect(websocket)
    user_id = current_user.id
    user_full_name = current_user.full_name
    bot_name = await asyncio.get_running_loop().run_in_executor(
        None, lambda: session.query(Bot).get(bot_id).name
    )

    try:
        await redis_dao.create_reader_task(manager, user_id, bot_id)
        while True:
            message = await websocket.receive_text()
            await redis_dao.publish_to_redis(user_id, bot_id, user_full_name, message)
            # bot_response = await redis_dao.get_bot_response_by_message(bot_id, message)
            bot_command = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: session.query(Command)
                .filter_by(bot_id=bot_id, message=message)
                .one_or_none(),
            )
            if bot_command:
                await redis_dao.publish_to_redis(
                    user_id, bot_id, bot_name, bot_command.response
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
