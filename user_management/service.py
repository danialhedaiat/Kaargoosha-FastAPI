import traceback

from core.database import SessionLocal, get_db
from core.settings import logger
from user_management.models import UserModel, UserSocialMediaID, Role
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

    def create_role(self, data):
        try:
            role = Role(name=data["role"])
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)

            return RoleResponseSchema.model_validate(role).model_dump_json()
        except Exception as exc:
            logger.error(traceback.format_exc())
            logger.error(exc)
            return {"message": str(exc)}

    @staticmethod
    def is_admin(user: UserModel) -> bool:
        if not user:
            return False

        return any(
            role.role.name == "admin"
            for role in user.role
        )
