from contextlib import contextmanager
from typing import Any, Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.app_utils import get_password_hash
from app.config import settings
from app.db_models import Bot, Command, RoleEnum, User

engine = create_engine(settings.sqlite_url, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)


def get_user(session: Session, username: str) -> Optional[User]:
    user = session.query(User).filter_by(username=username).one_or_none()
    return user


def insert_initial_data(session: Session) -> None:
    if session.query(User).count() == 0:
        session.bulk_save_objects(
            [
                User(
                    id=1,
                    username='admin',
                    hashed_password=get_password_hash('admin'),
                    full_name='Admin',
                    role=RoleEnum.ADMIN,
                ),
                Bot(id=0, name='ExampleBot', author_id=1),
                Command(id=0, message='Hey', response='Hi From Bot', bot_id=0),
            ]
        )


def init_db() -> None:
    import app.db_models as models  # pylint: disable=import-outside-toplevel

    models.Base.metadata.create_all(engine)

    with create_session() as session:
        insert_initial_data(session)


def teardown_db() -> None:
    import app.db_models as models  # pylint: disable=import-outside-toplevel

    models.Base.metadata.drop_all(engine)


@contextmanager
def create_session(**kwargs: Any) -> Iterator[Any]:
    new_session = SessionLocal(**kwargs)
    try:
        yield new_session
        new_session.commit()
    except Exception:
        new_session.rollback()
        raise
    finally:
        new_session.close()


def get_session() -> Any:
    with create_session() as session:
        yield session
