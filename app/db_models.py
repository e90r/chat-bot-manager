from enum import Enum

from sqlalchemy import Column, ForeignKey, Integer, String
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
    role = Column(String, nullable=False)


class Bot(Base):
    __tablename__ = 'Bot'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey('User.id'), nullable=False)

    author = relationship('User')
