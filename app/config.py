from pydantic import BaseSettings

ALGORITHM = 'HS256'
HISTORY_SIZE = 10


class EnvSettings(BaseSettings):
    redis_url: str
    sqlite_url: str
    secret_key: str
    server_url: str
    access_token_expire_minutes: int

    class Config:
        case_sensitive = False


settings = EnvSettings()
