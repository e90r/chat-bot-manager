from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from app.app_utils import get_password_hash
from app.authentication import authenticate_user, create_access_token, get_current_user
from app.config import settings
from app.db_models import RoleEnum, User
from app.db_utils import get_session, get_user
from app.pydantic_models import RegisterModel, RegisterResponse, Token, UserIdModel

router = APIRouter()


@router.post('/token')
def login_for_access_token(
    session: Session = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={'sub': user.username}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type='bearer')


@router.get('/users/me')
def read_users_me(current_user: User = Depends(get_current_user)) -> UserIdModel:
    return UserIdModel(user_id=current_user.id, role=current_user.role)


@router.post('/register')
def register(
    data: RegisterModel, session: Session = Depends(get_session)
) -> RegisterResponse:
    if get_user(session, data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Couldn't register user",
        )

    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role=RoleEnum.USER,
    )

    try:
        session.add(user)
        session.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Couldn't register user",
        ) from e

    return RegisterResponse(registered_username=user.username)
