from user_management.models import UserModel
from user_management.repository  import UserRepository


class UserService:

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

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