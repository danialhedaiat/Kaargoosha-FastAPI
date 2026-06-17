import datetime

from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column

from core.database import Base


class UserModel(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String(15), unique=True)
    is_verify: Mapped[bool] = mapped_column(Boolean, default=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    create_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.datetime.now())

    social_media = relationship(
        "UserSocialMediaID",
        back_populates='user',
        cascade='all, delete, delete-orphan',
    )
    roles = relationship("UserRole", back_populates="user", cascade='all, delete, delete-orphan')


class UserSocialMediaID(Base):
    __tablename__ = 'user_social_media_id'

    __table_args__ = (
        UniqueConstraint("username", "social_media", name="username_social_media_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    social_media: Mapped[str] = mapped_column(String(50), nullable=False)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=True)

    user = relationship("UserModel", back_populates="social_media")


class Role(Base):
    __tablename__ = "roles"

    __table_args__ = (
        UniqueConstraint("name", name="name_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)

    users = relationship("UserRole", back_populates="role", cascade="all, delete, delete-orphan")
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete, delete-orphan")  # 👈 "RolePermission" string not "role_permission" tablename


class RolePermission(Base):
    __tablename__ = "role_permission"

    __table_args__ = (
        UniqueConstraint("role_id", "codename", name="role_permission_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)  # 👈 removed duplicate
    codename: Mapped[str] = mapped_column(String(100), nullable=False)

    role = relationship("Role", back_populates="permissions")


class UserRole(Base):
    __tablename__ = "user_role"

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="user_role_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey('roles.id'), nullable=False)

    user = relationship("UserModel", back_populates="roles")
    role = relationship("Role", back_populates="users")


class UserBankInfo(Base):
    __tablename__ = "user_bank_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    card_number: Mapped[str] = mapped_column(String(16), nullable=True)
    account_number: Mapped[str] = mapped_column(String(26), nullable=True)
    iban_number: Mapped[str] = mapped_column(String(34), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    user = relationship("UserModel", backref="bank_info")