from asyncio import create_task
from threading import Lock
from typing import Any, List, Optional, Tuple

from aioredis import create_redis_pool

from app.config import HISTORY_SIZE, settings
from app.connection_manager import ConnectionManager
from app.pydantic_models import CommandModel


class RedisDao:
    def __init__(self) -> None:
        self.redis: Any = None

    async def init_conn(self) -> None:
        if self.redis is None:
            self.redis = await create_redis_pool(settings.redis_url)

    async def add_bot_commands_list(
        self, bot_id: int, commands: List[CommandModel]
    ) -> None:
        for item in commands:
            await self.add_bot_command(bot_id, item)

    async def add_bot_command(self, bot_id: int, command_model: CommandModel) -> None:
        if await self.redis.hget(f'{bot_id}:msg', command_model.command):
            raise CommandExistsError

        await self.redis.hset(
            f'{bot_id}:id', IdGenerator.generate_id(), command_model.command
        )
        await self.redis.hset(
            f'{bot_id}:msg', command_model.command, command_model.response
        )

    async def get_bot_commands(self, bot_id: int) -> List[Any]:
        result = []
        ids = await self.redis.hgetall(f'{bot_id}:id')
        commands = await self.redis.hgetall(f'{bot_id}:msg')
        for command_id, command in ids.items():
            result.append(
                {
                    'command_id': command_id,
                    'command': command.decode(),
                    'response': commands[command].decode(),
                }
            )

        return result

    async def get_bot_response_by_message(
        self, bot_id: int, message: str
    ) -> Optional[str]:
        command = await self.redis.hget(f'{bot_id}:msg', message)
        if not command:
            return None

        return command.decode()

    async def edit_bot_command(
        self, bot_id: int, command_id: int, new_response: str
    ) -> None:
        command = await self.redis.hget(f'{bot_id}:id', command_id)
        if not command:
            raise CommandDoesNotExistError

        await self.redis.hset(f'{bot_id}:msg', command, new_response)

    async def get_bot_command(
        self, bot_id: int, command_id: int
    ) -> Optional[Tuple[str, str]]:
        command = await self.redis.hget(f'{bot_id}:id', command_id)
        if not command:
            return None

        response = await self.redis.hget(f'{bot_id}:msg', command)
        return command.decode(), response.decode()

    async def delete_bot_command(self, bot_id: int, command_id: int) -> None:
        command = await self.redis.hget(f'{bot_id}:id', command_id)
        if not command:
            raise CommandDoesNotExistError

        await self.redis.hdel(f'{bot_id}:id', command_id)
        await self.redis.hdel(f'{bot_id}:msg', command)

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


class RedisConnNotInitializedError(Exception):
    pass


class CommandExistsError(Exception):
    pass


class CommandDoesNotExistError(Exception):
    pass
