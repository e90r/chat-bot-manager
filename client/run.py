import asyncio
from typing import Any, Dict, List

from aioconsole import ainput, aprint
from aiohttp import ClientSession, WSMsgType

SERVER_URL = 'http://127.0.0.1:8000'


async def sign_in() -> Dict[str, str]:
    username = await ainput('Username: ')
    password = await ainput('Password: ')
    data = {'username': username, 'password': password}

    async with ClientSession() as session:
        async with session.post(f'{SERVER_URL}/token', data=data) as response:
            if response.status == 401:
                raise RuntimeError('Wrong credentials!')

            json = await response.json()
            token = json['access_token']
            header = {'Authorization': f'Bearer {token}'}
            return header


async def load_messages_history(
    auth: Dict[str, str], user_id: int, bot_id: int
) -> List[str]:
    async with ClientSession(headers=auth) as session:
        async with session.get(
            f'{SERVER_URL}/bots/{bot_id}/messages/{user_id}'
        ) as response:
            json = await response.json()
            return json['history']


async def run_client(auth: Dict[str, str], bot_id: int) -> None:
    async with ClientSession() as session:
        async with session.ws_connect(
            f'{SERVER_URL}/ws/{bot_id}',
            autoclose=False,
            headers=auth,
        ) as ws:
            await asyncio.gather(receive_messages(ws), send_messages(ws))


async def receive_messages(websocket: Any) -> None:
    async for msg in websocket:
        if msg.type == WSMsgType.TEXT:
            await aprint(msg.data)
        elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
            break


async def send_messages(websocket: Any) -> None:
    while True:
        msg = await ainput()
        await websocket.send_str(msg)


async def get_user_id(auth: Dict[str, str]) -> int:
    async with ClientSession(headers=auth) as session:
        async with session.get(f'{SERVER_URL}/users/me') as response:
            json = await response.json()
            return json['user_id']


async def enter_bot_id() -> int:
    bot_id = await ainput('Select bot id: ')
    return bot_id


async def get_commands(auth: Dict[str, str], bot_id: int) -> Any:
    async with ClientSession(headers=auth) as session:
        async with session.get(f'{SERVER_URL}/bots/{bot_id}/commands') as response:
            json = await response.json()
            return json['commands']


async def get_available_bots(auth: Dict[str, str]) -> Any:
    async with ClientSession(headers=auth) as session:
        async with session.get(f'{SERVER_URL}/bots') as response:
            json = await response.json()
            return json['bots']


async def get_available_commands(auth: Dict[str, str], bot_id: int) -> Any:
    async with ClientSession(headers=auth) as session:
        async with session.get(f'{SERVER_URL}/bots/{bot_id}/commands') as response:
            json = await response.json()
            return json['commands']


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    auth_header = loop.run_until_complete(sign_in())
    user = loop.run_until_complete(get_user_id(auth_header))
    available_bots = loop.run_until_complete(get_available_bots(auth_header))

    for bot in available_bots:
        print(bot)

    bot = loop.run_until_complete(enter_bot_id())
    commands = loop.run_until_complete(get_available_commands(auth_header, bot))

    print('Commands:')
    for command in commands:
        print(command)

    print('Start chatting!')

    history = loop.run_until_complete(load_messages_history(auth_header, user, bot))

    for message in history:
        print(message)

    loop.run_until_complete(run_client(auth_header, bot))
