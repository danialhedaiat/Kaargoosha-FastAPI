from core.database import SessionLocal, get_db
from user_management.models import UserModel, UserSocialMediaID


class UserService:

    def __init__(self):
        self.db: SessionLocal = get_db()

    def check_phone_number_exist(self, data):
        exists = self.db.query(UserModel).filter_by(phone_number=data["phone_number"]).all()
        if exists:
            return {"message": "User already exists"}
        return {"message": "User does not exist"}


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