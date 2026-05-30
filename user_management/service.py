import json
import traceback

from sqlalchemy.exc import IntegrityError

from core.database import SessionLocal, get_db
from core.settings import logger, settings
from user_management.models import UserModel, UserSocialMediaID, Role, UserRole, RolePermission
from user_management.permissions import Permissions, permission
from user_management.schema import UserCompleteSchema, RoleResponseSchema, AssignRoleResponseSchema, \
    RolePermissionResponseSchema


class UserService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def check_phone_number_exist(self, data):
        exists = self.db.query(UserModel).filter_by(phone_number=data["phone_number"]).all()
        if exists:
            return json.dumps({"message": "User already exists"})
        return json.dumps({"error": "User does not exist"})

    def get_user_by_username(self, data):
        user_social_media = self.db.query(UserSocialMediaID).filter_by(username=data["username"],
                                                                       social_media=data["social_media"]).first()
        if not user_social_media:
            return json.dumps({"error": "User does not exist"})
        return UserCompleteSchema.model_validate(user_social_media.user).model_dump_json()

    def create_user(self, data):
        try:
            with self.db.begin():
                user = UserModel(
                    phone_number=data["phone_number"],
                    first_name=data["first_name"],
                    last_name=data["last_name"]
                )
                self.db.add(user)

                self.db.flush()

                exists = self.db.query(UserSocialMediaID).filter_by(
                    username=data["username"],
                    social_media=data["social_media"]
                ).first()
                if exists:
                    raise Exception("User already exists")
                user_social_media = UserSocialMediaID(
                    user_id=user.id,
                    username=data["username"],
                    social_media=data["social_media"]
                )

                self.db.add(user_social_media)

            return UserCompleteSchema.model_validate(user).model_dump_json()
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def join_user(self, data):
        try:
            user = self.db.query(UserModel).filter_by(phone_number=data["phone_number"]).first()
            exists = self.db.query(UserSocialMediaID).filter_by(
                username=data["username"],
                social_media=data["social_media"]
            ).first()
            if exists:
                raise Exception("User already joined")
            user_social_media = UserSocialMediaID(
                user_id=user.id,
                username=data["username"],
                social_media=data["social_media"]
            )

            self.db.add(user_social_media)
            self.db.commit()
            self.db.refresh(user_social_media)
            return UserCompleteSchema.model_validate(user).model_dump_json()

        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    def check_admin_menu_permission(self, data):
        try:
            user_roles = self.db.query(UserRole).filter_by(user_id=data["user_id"]).all()
            check_permission = any(role_permission.codename == Permissions.USER_ADMIN
                                   for user_role in user_roles
                                   for role_permission in user_role.permissions
                                   )
            if check_permission or data["phone_number"] == settings.GOD:
                return json.dumps({"message": "User is Admin", "status": True})
            return json.dumps({"message": "User is not Admin", "status": False})
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.USER_DELETE)
    def delete(self, data):
        pass


class RoleService:

    def __init__(self):
        self.db: SessionLocal = get_db()


    @permission(Permissions.ROLE_CREATE)
    def create_role(self, data: dict):
        try:
            role = Role(name=data["name"])
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)
            return RoleResponseSchema().model_validate(role).model_dump_json()
        except IntegrityError:
            self.db.rollback()
            return json.dumps({"error": "Role already exists"})
        except Exception as e:
            self.db.rollback()
            logger.error(e)
            return json.dumps({"error": str(e)})


    @permission(Permissions.ROLE_READ)
    def get_all_roles(self):
        roles = self.db.query(Role).all()
        return json.dumps({"roles": [
            RoleResponseSchema.model_validate(role).model_dump()
            for role in roles]
        },  ensure_ascii=False)

    @permission(Permissions.ROLE_READ)
    def get_role(self, role_id: int):
        role = self.db.query(Role).filter_by(id=role_id).first()
        if not role:
            return {"error": "Role not found"}
        return RoleResponseSchema().model_validate(role).model_dump_json()


    @permission(Permissions.ROLE_DELETE)
    def delete_role(self, role_id: int):
        try:
            role = self.db.query(Role).filter_by(id=role_id).first()
            if not role:
                return json.dumps({"error": "Role not found"})

            self.db.delete(role)
            self.db.commit()
            return json.dumps({"message": "deleted"})
        except Exception as e:
            self.db.rollback()
            logger.error(e)
            return json.dumps({"error": str(e)})

    # ── Assign / Revoke roles on users ─────────────────────────

    @permission(Permissions.ROLE_ASSIGN)
    def assign_role(self, data: dict):
        """data = {requested_by, user_id, role_id}"""
        try:
            user = self.db.query(UserModel).filter_by(id=data["user_id"]).first()
            if not user:
                return json.dumps({"error": "User not found"})

            role = self.db.query(Role).filter_by(id=data["role_id"]).first()
            if not role:
                return json.dumps({"error": "Role not found"})

            user_role = UserRole(user_id=data["user_id"], role_id=data["role_id"])
            self.db.add(user_role)
            self.db.commit()
            return AssignRoleResponseSchema().model_validate(user_role).model_dump_json()
        except Exception as e:
            self.db.rollback()
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.ROLE_REVOKE)
    def revoke_role(self, data: dict):
        """data = {requested_by, user_id, role_id}"""
        try:
            user_role = self.db.query(UserRole).filter_by(
                user_id=data["user_id"], role_id=data["role_id"]
            ).first()
            if not user_role:
                return json.dumps({"error": "User does not have this role"})

            self.db.delete(user_role)
            self.db.commit()
            return json.dumps({"message": "role revoked"})
        except Exception as e:
            self.db.rollback()
            logger.error(e)
            return json.dumps({"error": str(e)})

    @permission(Permissions.ROLE_READ)
    def get_user_roles(self, user_id: int):
        user = self.db.query(UserModel).filter_by(id=user_id).first()
        if not user:
            return json.dumps({"error": "User not found"})
        return [AssignRoleResponseSchema().model_validate(user_role).model_dump_json() for user_role in user.role]


class PermissionService:
    def __init__(self):
        self.db = get_db()

    # ── Permission CRUD ────────────────────────────────────────

    @permission(Permissions.PERMISSION_CREATE)
    def create_permission(self, data: dict):
        role_permission = RolePermission(role_id=data["role_id"], codename=data["codename"])
        self.db.add(role_permission)
        self.db.commit()
        self.db.refresh(role_permission)

        return RolePermissionResponseSchema().model_validate(role_permission).model_dump_json()

    @permission(Permissions.PERMISSION_READ)
    def get_all_permissions(self):
        return Permissions().__dict__

    @permission(Permissions.PERMISSION_DELETE)
    def delete_permission_from_role(self, data: dict):
        permission = self.db.query(RolePermission).filter_by(codename=data["permission_codename"]).first()
        if not permission:
            return {"error": "Permission not found"}

        role_permission = self.db.query(RolePermission).filter_by(
            role_id=data["role_id"], permission_id=permission.id
        ).first()
        if not role_permission:
            return {"error": "Role does not have this permission"}

        self.db.delete(role_permission)
        self.db.commit()
        return {"status": "revoked"}

    @permission(Permissions.PERMISSION_READ)
    def get_role_permissions(self, data: dict):
        role = self.db.query(Role).filter_by(id=data["role_id"]).first()
        if not role:
            return {"error": "Role not found"}
        return [
            RolePermissionResponseSchema().model_validate(role_permission).model_dump_json()
            for role_permission in role.permission
        ]
