from typing import Any, Dict, List

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


class RegisterModel(BaseModel):
    username: str
    password: str
    full_name: str


class RegisterResponse(BaseModel):
    registered_username: str


class BotResponse(BaseModel):
    bot_id: int
    bot_name: str
    author_username: str


class GetBotsResponse(BaseModel):
    bots: List[BotResponse]


class CommandModel(BaseModel):
    command: str
    response: str


class AddBotModel(BaseModel):
    name: str
    commands: List[CommandModel]


class AddBotResponse(BaseModel):
    bot_id: int
    name: str
    author: str


class EditBotCommandModel(BaseModel):
    new_response: str


class UserIdModel(BaseModel):
    user_id: int
    role: str


class GetBotCommandsResponse(BaseModel):
    bot_name: str
    commands: List[Any]


class AddBotCommandResponse(BaseModel):
    bot_name: str
    added_command: Dict[str, str]
    author_username: str


class EditBotCommandResponse(BaseModel):
    bot_name: str
    command: str
    new_response: str


class DeleteBotCommandResponse(BaseModel):
    bot_name: str
    deleted_command_id: int


class GetHistoryResponse(BaseModel):
    history: List[str]
