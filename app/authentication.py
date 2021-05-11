from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette import status

from app.app_utils import verify_password
from app.config import ALGORITHM, settings
from app.db_models import RoleEnum, User
from app.db_utils import get_session, get_user
from app.pydantic_models import TokenData


class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, req: Request = None, ws: WebSocket = None) -> Any:  # type: ignore
        return await super().__call__(req or ws)  # type: ignore


oauth2_scheme = CustomOAuth2PasswordBearer(tokenUrl='token')


def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    user = get_user(session, username)

    if not user or not verify_password(password, user.hashed_password):
        return None

    return user


def create_access_token(
    data: Dict[Any, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)
) -> Optional[User]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        raise credentials_exception from e

    user = get_user(session, token_data.username)
    if user is None:
        raise credentials_exception

    return user


def verify_role_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Permission denied',
        )

    return current_user
