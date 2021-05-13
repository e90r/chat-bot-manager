from enum import Enum

from sqlalchemy import Column
from sqlalchemy import Enum as AlchEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import relationship

Base: DeclarativeMeta = declarative_base()


class RoleEnum(str, Enum):
    ADMIN = 'admin'
    USER = 'user'


class User(Base):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(AlchEnum(RoleEnum), nullable=False)


class Bot(Base):
    __tablename__ = 'Bot'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey('User.id'), nullable=False)

    author = relationship('User')
    commands = relationship('Command')


class Command(Base):
    __tablename__ = 'Command'

    id = Column(Integer, primary_key=True)
    message = Column(String, unique=True, nullable=False)
    response = Column(String, nullable=False)
    bot_id = Column(Integer, ForeignKey('Bot.id'), nullable=False)

    bot = relationship('Bot')
