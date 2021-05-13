from asyncio import create_task
from threading import Lock
from typing import Any, List

from aioredis import create_redis_pool

from app.config import HISTORY_SIZE, settings
from app.connection_manager import ConnectionManager


class RedisDao:
    def __init__(self) -> None:
        self.redis: Any = None

    async def init_conn(self) -> None:
        if self.redis is None:
            self.redis = await create_redis_pool(settings.redis_url)

    async def get_history_from_redis(self, user_id: int, bot_id: int) -> List[str]:
        history_key = f'hist:{user_id}:{bot_id}'
        await self.redis.ltrim(history_key, -HISTORY_SIZE, -1)
        history = await self.redis.lrange(history_key, 0, -1)
        return history if history is not None else []

    async def publish_to_redis(
        self, user_id: int, bot_id: int, login: str, message: str
    ) -> None:
        history_key = f'hist:{user_id}:{bot_id}'
        channel = f'ch:{user_id}:{bot_id}'
        text = f'{login}: {message}'
        await self.redis.rpush(history_key, text)
        await self.redis.publish(channel, text)

    async def create_reader_task(
        self, manager: ConnectionManager, user_id: int, bot_id: int
    ) -> None:
        async def reader(ch: Any) -> None:
            while await ch.wait_message():
                msg = (await ch.get()).decode()
                await manager.broadcast(msg)

        channel = f'ch:{user_id}:{bot_id}'
        channels = await self.redis.subscribe(channel)
        create_task(reader(channels[0]))

    async def close_redis_connection(self) -> None:
        self.redis.close()
        await self.redis.wait_closed()


redis_dao = RedisDao()


class IdGenerator:
    cur_id: int = 0
    lock: Lock = Lock()

    @classmethod
    def generate_id(cls) -> str:
        with cls.lock:
            cls.cur_id += 1
            return str(cls.cur_id)
