from fastapi import APIRouter, FastAPI

from app.handlers import (
    add_bot,
    add_bot_command,
    delete_bot_command,
    edit_bot_command,
    get_bot_commands,
    get_bots,
    get_messages,
    login_for_access_token,
    on_shutdown,
    on_startup,
    read_users_me,
    register,
    websocket_endpoint,
)


def create_app() -> FastAPI:
    app = FastAPI()

    router = APIRouter()

    router.add_event_handler('shutdown', on_shutdown)
    router.add_event_handler('startup', on_startup)

    router.add_api_route('/token', login_for_access_token, methods=['POST'])
    router.add_api_route('/users/me', read_users_me, methods=['GET'])
    router.add_api_route('/register', register, methods=['POST'])
    router.add_api_route('/bots', get_bots, methods=['GET'])
    router.add_api_route('/bots', add_bot, methods=['POST'])
    router.add_api_route('/bots/{bot_id}/commands', get_bot_commands, methods=['GET'])
    router.add_api_route('/bots/{bot_id}/commands', add_bot_command, methods=['POST'])
    router.add_api_route(
        '/bots/{bot_id}/commands/{command_id}', edit_bot_command, methods=['PATCH']
    )
    router.add_api_route(
        '/bots/{bot_id}/commands/{command_id}', delete_bot_command, methods=['DELETE']
    )
    router.add_api_route(
        '/bots/{bot_id}/messages/{user_id}', get_messages, methods=['GET']
    )

    router.add_api_websocket_route('/ws/{user_id}/{bot_id}', websocket_endpoint)

    app.include_router(router)

    return app
