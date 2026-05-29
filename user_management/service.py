import traceback

from sqlalchemy.exc import IntegrityError

from core.database import SessionLocal, get_db
from core.settings import logger
from user_management.models import UserModel, UserSocialMediaID, Role, UserRole
from user_management.schema import UserCompleteSchema, RoleResponseSchema


class UserService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def check_phone_number_exist(self, data):
        exists = self.db.query(UserModel).filter_by(phone_number=data["phone_number"]).all()
        if exists:
            return {"message": "User already exists"}
        return {"error": "User does not exist"}

    def get_user_by_username(self, data):
        user_social_media = self.db.query(UserSocialMediaID).filter_by(username=data["username"],
                                                                       social_media=data["social_media"]).first()
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
            return {"error": str(e)}

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

            return UserCompleteSchema.model_validate(user).model_dump_json()
        except Exception as e:
            self.db.rollback()
            logger.error(traceback.format_exc())
            logger.error(e)
            return {"error": str(e)}

    def delete(self, data):
        pass


class RoleService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def create_role(self, data: dict):
        try:
            role = Role(name=data["name"])
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)
            return {"id": role.id, "name": role.name}
        except IntegrityError:
            self.db.rollback()
            return {"error": "Role already exists"}
        except Exception as e:
            self.db.rollback()
            logger.error(e)
            return {"error": str(e)}

    def get_all_roles(self):
        roles = self.db.query(Role).all()
        return [{"id": role.id, "name": role.name} for role in roles]

    def get_role(self, role_id: int):
        role = self.db.query(Role).filter_by(id=role_id).first()
        if not role:
            return {"error": "Role not found"}
        return {"id": role.id, "name": role.name}

    def delete_role(self, role_id: int):
        try:
            role = self.db.query(Role).filter_by(id=role_id).first()
            if not role:
                return {"error": "Role not found"}

            self.db.delete(role)
            self.db.commit()
            return {"status": "deleted"}
        except Exception as e:
            self.db.rollback()
            logger.error(e)
            return {"error": str(e)}

    # ── Assign / Revoke roles on users ─────────────────────────

    def assign_role(self, data: dict):
        """data = {requested_by, user_id, role_id}"""
        try:
            user = self.db.query(UserModel).filter_by(id=data["user_id"]).first()
            if not user:
                return {"error": "User not found"}

            role = self.db.query(Role).filter_by(id=data["role_id"]).first()
            if not role:
                return {"error": "Role not found"}

            user_role = UserRole(user_id=data["user_id"], role_id=data["role_id"])
            self.db.add(user_role)
            self.db.commit()
            return {"status": "role assigned", "user_id": data["user_id"], "role_id": data["role_id"]}
        except Exception as e:
            self.db.rollback()
            logger.error(e)
            return {"error": str(e)}

    @staticmethod
    def is_admin(user: UserModel) -> bool:
        if not user:
            return False

        return any(
            role.role.name == "admin"
            for role in user.role
        )
