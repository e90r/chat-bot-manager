import pytest

from app.app_utils import verify_password
from app.db_models import Command, RoleEnum, User


@pytest.mark.asyncio()
async def test_register(session, client):
    response = await client.post(
        '/register',
        json={'username': 'some_user', 'password': '123', 'full_name': 'Testing'},
    )

    user = session.query(User).filter_by(username='some_user').one()

    assert user.username == 'some_user'
    assert verify_password('123', user.hashed_password)
    assert user.full_name == 'Testing'

    assert response.status_code == 200
    assert response.json() == {'registered_username': 'some_user'}


@pytest.mark.asyncio()
async def test_register_same_user(client):
    response = await client.post(
        '/register',
        json={'username': 'admin', 'password': '123', 'full_name': 'Testing'},
    )

    assert response.status_code == 409
    assert response.json()['detail'] == "Couldn't register user"


@pytest.mark.asyncio()
@pytest.mark.usefixtures('mock_auth')
async def test_login(client, token_admin):
    response = await client.post(
        '/token',
        form=[
            ('username', 'admin'),
            ('password', 'admin'),
        ],
    )

    assert response.status_code == 200
    assert response.json() == {'access_token': token_admin, 'token_type': 'bearer'}


@pytest.mark.asyncio()
@pytest.mark.usefixtures('mock_auth')
async def test_login_wrong_password(client):
    response = await client.post(
        '/token',
        form=[
            ('username', 'admin'),
            ('password', '123'),
        ],
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Incorrect username or password'


@pytest.mark.asyncio()
async def test_read_users_me(client, auth_header_admin):
    response = await client.get('/users/me', headers=auth_header_admin)

    assert response.status_code == 200
    assert response.json() == {'user_id': 1, 'role': RoleEnum.ADMIN.value}


@pytest.mark.asyncio()
async def test_not_authenticated(client):
    response = await client.get('/users/me')

    assert response.status_code == 401
    assert response.json()['detail'] == 'Not authenticated'


@pytest.mark.asyncio()
async def test_wrong_token(client):
    response = await client.get('/users/me', headers={'Authorization': 'Bearer foobar'})

    assert response.status_code == 401
    assert response.json()['detail'] == 'Could not validate credentials'


@pytest.mark.asyncio()
@pytest.mark.usefixtures('bot')
async def test_get_bots(client, auth_header_admin):
    response = await client.get('/bots', headers=auth_header_admin)

    assert response.status_code == 200
    assert response.json() == {
        'bots': [{'bot_id': 1, 'bot_name': 'test_bot', 'author_username': 'admin'}]
    }


@pytest.mark.asyncio()
async def test_add_bot(client, auth_header_admin):
    response = await client.post(
        '/bots',
        headers=auth_header_admin,
        json={'name': 'bot', 'commands': [{'command': 'Hi', 'response': 'Welcome'}]},
    )

    # assert response.status_code == 200
    assert response.json() == {'bot_id': 1, 'name': 'bot', 'author': 'admin'}


@pytest.mark.asyncio()
async def test_add_bot_no_permission(client, auth_header_user):
    response = await client.post(
        '/bots',
        headers=auth_header_user,
        json={'name': 'bot', 'commands': [{'command': 'Hi', 'response': 'Welcome'}]},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Permission denied'


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_get_bot_commands(client, auth_header_admin):
    response = await client.get('/bots/1/commands', headers=auth_header_admin)

    assert response.status_code == 200
    assert response.json() == {
        'bot_name': 'test_bot',
        'commands': [
            {'command_id': 1, 'command': 'Hello', 'response': 'Hello from bot!'}
        ],
    }


@pytest.mark.asyncio()
@pytest.mark.usefixtures('bot')
async def test_add_bot_command(client, auth_header_admin, session):
    response = await client.post(
        '/bots/1/commands',
        headers=auth_header_admin,
        json={'command': 'Hi', 'response': 'Welcome'},
    )

    added_cmd_resp = (
        session.query(Command).filter_by(bot_id=1, message='Hi').one().response
    )

    assert added_cmd_resp == 'Welcome'
    assert response.status_code == 200
    assert response.json() == {
        'bot_name': 'test_bot',
        'added_command': {'command': 'Hi', 'response': 'Welcome'},
        'author_username': 'admin',
    }


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_add_bot_command_not_unique(client, auth_header_admin):
    response = await client.post(
        '/bots/1/commands',
        headers=auth_header_admin,
        json={'command': 'Hello', 'response': 'Some response'},
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Command already exists'


@pytest.mark.asyncio()
async def test_add_bot_command_no_permission(client, auth_header_user):
    response = await client.post(
        '/bots/1/commands',
        headers=auth_header_user,
        json={'command': 'Hello', 'response': 'Some response'},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Permission denied'


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_delete_bot_command(client, auth_header_admin, session):
    response = await client.delete('/bots/1/commands/1', headers=auth_header_admin)

    deleted_cmd_resp = (
        session.query(Command).filter_by(bot_id=1, message='Hello').one_or_none()
    )

    assert deleted_cmd_resp is None
    assert response.status_code == 200
    assert response.json() == {'bot_name': 'test_bot', 'deleted_command_id': 1}


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_delete_bot_command_nonexistent(client, auth_header_admin):
    response = await client.delete('/bots/1/commands/10', headers=auth_header_admin)

    assert response.status_code == 400
    assert response.json()['detail'] == 'Command does not exist'


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_delete_bot_command_no_permission(client, auth_header_user):
    response = await client.delete('/bots/1/commands/0', headers=auth_header_user)

    assert response.status_code == 403
    assert response.json()['detail'] == 'Permission denied'


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_edit_bot_command(client, auth_header_admin, session):
    response = await client.patch(
        '/bots/1/commands/1',
        headers=auth_header_admin,
        json={'new_response': 'Hi Again'},
    )

    edited_cmd_resp = (
        session.query(Command).filter_by(bot_id=1, message='Hello').one().response
    )

    assert edited_cmd_resp == 'Hi Again'
    assert response.status_code == 200
    assert response.json() == {
        'bot_name': 'test_bot',
        'command': 'Hello',
        'new_response': 'Hi Again',
    }


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_edit_bot_command_nonexistent(client, auth_header_admin):
    response = await client.patch(
        '/bots/1/commands/10',
        headers=auth_header_admin,
        json={'new_response': 'Hi Again'},
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'Command does not exist'


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_edit_bot_command_no_permission(client, auth_header_user):
    response = await client.patch(
        '/bots/1/commands/10',
        headers=auth_header_user,
        json={'new_response': 'Hi Again'},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Permission denied'


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_existed_bot_message')
async def test_get_messages_history(client, auth_header_admin):
    response = await client.get('/bots/1/messages/1', headers=auth_header_admin)

    assert response.status_code == 200
    assert response.json() == {'history': ['admin: first message']}


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_existed_bot_message')
async def test_get_messages_history_not_matching_id(client, auth_header_admin):
    response = await client.get('/bots/1/messages/2', headers=auth_header_admin)

    assert response.status_code == 403
    assert response.json()['detail'] == 'Permission denied'


@pytest.mark.asyncio()
@pytest.mark.usefixtures('_hello_message')
async def test_websocket_chat_admin(client, auth_header_admin):
    async with client.websocket_connect('/ws/1', headers=auth_header_admin) as ws:
        message = 'test'
        await ws.send_text(message)
        text = await ws.receive_text()
        assert text == f'Admin: {message}'

        message = 'Hello'
        await ws.send_text(message)
        text = await ws.receive_text()
        assert text == f'Admin: {message}'

        text = await ws.receive_text()
        assert text == 'test_bot: Hello from bot!'
