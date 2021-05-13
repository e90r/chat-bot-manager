from fastapi import FastAPI

from app.redis_utils import redis_dao
from app.routers import bots, chat, users


async def on_startup() -> None:
    await redis_dao.init_conn()


async def on_shutdown() -> None:
    await redis_dao.close_redis_connection()


def create_app() -> FastAPI:
    app = FastAPI()

    app.include_router(bots.router)
    app.include_router(users.router)
    app.include_router(chat.router)

    app.add_event_handler('startup', on_startup)
    app.add_event_handler('shutdown', on_shutdown)

    return app
