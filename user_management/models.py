import datetime

from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column

from core.database import Base


class UserModel(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String(15), unique=True)
    is_verify: Mapped[bool]= mapped_column(Boolean, default=False)
    first_name: Mapped[str]= mapped_column(String(50), nullable=False)
    last_name: Mapped[str]= mapped_column(String(50), nullable=False)
    create_date: Mapped[datetime]= mapped_column(DateTime, default=datetime.datetime.now())

    user_social_medias = relationship(
        "UserSocialMediaID",
        back_populates='user',
        cascade='all, delete, delete-orphan',
    )
    role = relationship("UserRole", back_populates="user", cascade='all, delete, delete-orphan')


class UserSocialMediaID(Base):
    __tablename__ = 'user_social_media_id'

    __table_args__ = (
        UniqueConstraint("username", "social_media", name="username_social_media_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    social_media: Mapped[str] = mapped_column(String(50), nullable=False)

    user = relationship("UserModel", back_populates="user_social_medias")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)

    user = relationship("UserRole", back_populates="role", cascade="all, delete, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_role"

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="user_role_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    role_id = mapped_column(Integer, ForeignKey('roles.id'), nullable=False)

    user = relationship("UserModel", back_populates="role")
    role = relationship("Role", back_populates="user")
