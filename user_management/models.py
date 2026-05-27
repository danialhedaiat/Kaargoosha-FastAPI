import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from core.database import Base


class UserModel(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(15), unique=True)
    is_verify = Column(Boolean, default=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    create_date = Column(DateTime, default=datetime.datetime.now())

    user_social_medias = relationship(
        "UserSocialMediaID",
        back_populates='user',
        cascade='all, delete, delete-orphan',
    )
    role = relationship("UserRole", back_populates="user", cascade='all, delete, delete-orphan')


class UserSocialMediaID(Base):
    __tablename__ = 'user_social_media_id'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    username = Column(String(100), nullable=False)
    social_media = Column(String(50), nullable=False)

    user = relationship("UserModel", back_populates="user_social_medias")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), nullable=False)

    user = relationship("UserRole", back_populates="role", cascade="all, delete, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_role"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)

    user = relationship("UserModel", back_populates="role")
    role = relationship("Role", back_populates="user")
