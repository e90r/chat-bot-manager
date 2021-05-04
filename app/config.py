from pydantic import BaseSettings

ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
HISTORY_SIZE = 10


class EnvSettings(BaseSettings):
    redis_url: str = 'redis://localhost:6379/0'
    sqlite_url: str = 'sqlite:///application.db'
    secret_key: str = '2b38c28a4d952320bcabe59f061622785279c757db1e2e128b054635922136bd'
    server_url: str = 'http://localhost:8000'

    class Config:
        case_sensitive = False


settings = EnvSettings()
