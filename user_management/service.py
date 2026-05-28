from core.database import SessionLocal, get_db
from core.settings import logger
from user_management.models import UserModel, UserSocialMediaID
from user_management.schema import UserCompleteSchema


class UserService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def check_phone_number_exist(self, data):
        exists = self.db.query(UserModel).filter_by(phone_number=data["phone_number"]).all()
        if exists:
            return {"message": "User already exists"}
        return {"message": "User does not exist"}

    def create(self, data):
        try:
            with self.db.begin():
                user = UserModel(
                    phone_number=data["phone_number"],
                    first_name=data["first_name"],
                    last_name=data["last_name"]
                )
                self.db.add(user)

                self.db.flush()  # 👈 gets user.id without commit

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
            import traceback
            logger.error(traceback.format_exc())
            logger.error(e)
            return {"message": str(e)}

    def delete(self, data):

        requester_id = data["requested_by"]
        target_user_id = data["user_id"]

        requester = self.user_repo.get(requester_id)

        if not RoleService.is_admin(requester):
            return {"error": "forbidden"}

        self.user_repo.delete(target_user_id)

        return {"status": "deleted"}


class RoleService:

    @staticmethod
    def is_admin(user: UserModel) -> bool:
        if not user:
            return False

        return any(
            role.role.name == "admin"
            for role in user.role
        )
