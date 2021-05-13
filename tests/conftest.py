# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Dict, Optional

import pytest
from async_asgi_testclient import TestClient
from fakeredis import FakeServer, aioredis
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.app_utils import get_password_hash
from app.config import ALGORITHM, settings
from app.db_models import Bot, Command, RoleEnum, User
from app.db_utils import get_session
from app.factory import create_app
from app.redis_utils import redis_dao

test_engine = create_engine(
    'sqlite:///test.db', connect_args={'check_same_thread': False}
)
TestingSessionLocal = sessionmaker(bind=test_engine)


def create_access_token_without_expire(
    data: Dict[Any, Any], expires_delta: Optional[timedelta] = None
):  # pylint: disable=unused-argument
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


@contextmanager
def create_test_session():
    new_session = TestingSessionLocal()
    try:
        yield new_session
        new_session.commit()
    except Exception:
        new_session.rollback()
        raise
    finally:
        new_session.close()


@pytest.fixture()
def session():
    with create_test_session() as sess:
        yield sess


def test_session():
    with create_test_session() as sess:
        yield sess


@pytest.fixture()
def mock_auth(mocker):
    mocker.patch(
        'app.routers.users.create_access_token',
        side_effect=create_access_token_without_expire,
    )


@pytest.fixture(autouse=True)
def create_test_database(test_app):
    test_app.dependency_overrides[get_session] = test_session

    import app.db_models as models  # pylint: disable=import-outside-toplevel

    models.Base.metadata.create_all(test_engine)
    with create_test_session() as session:
        if session.query(User).count() == 0:
            session.bulk_save_objects(
                [
                    User(
                        id=1,
                        username='admin',
                        hashed_password=get_password_hash('admin'),
                        full_name='Admin',
                        role=RoleEnum.ADMIN,
                    )
                ]
            )
    yield
    models.Base.metadata.drop_all(test_engine)


@pytest.fixture()
def auth_header_user(session, token_user):
    user = User(
        username='test_user',
        hashed_password=get_password_hash('123'),
        full_name='Test',
        role=RoleEnum.USER,
    )
    session.add(user)
    session.commit()
    header = {'Authorization': f'Bearer {token_user}'}
    return header


@pytest.fixture()
def auth_header_admin(token_admin):
    header = {'Authorization': f'Bearer {token_admin}'}
    return header


@pytest.fixture()
def test_app():
    return create_app()


@pytest.fixture()
async def client(test_app):
    async with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
async def fake_redis(mocker):
    fake_redis_instance = await aioredis.create_redis_pool(server=FakeServer())
    mocker.patch.object(redis_dao, 'redis', fake_redis_instance)
    yield
    await redis_dao.close_redis_connection()


@pytest.fixture()
def token_user():
    return (
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
        'eyJzdWIiOiJ0ZXN0X3VzZXIifQ.y1pHz7cgOJkjSgv9XZdU4pLftW_eCN6oGPwZVklEsZ4'
    )


@pytest.fixture()
def token_admin():
    return (
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
        'eyJzdWIiOiJhZG1pbiJ9.YoOwYabm0HCgarIy9KejmTEVIyx2somDHJfhsCv1uWY'
    )


@pytest.fixture()
async def bot(session):
    bot = Bot(id=1, name='test_bot', author_id=1)
    session.add(bot)
    session.commit()


@pytest.fixture()
async def _hello_message(bot, session):
    command = Command(id=1, message='Hello', response='Hello from bot!', bot_id=1)
    session.add(command)
    session.commit()


@pytest.fixture()
async def _existed_bot_message(bot):
    await redis_dao.redis.rpush('hist:1:1', 'admin: first message')
