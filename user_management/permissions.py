import functools

from core.settings import settings, logger
from user_management.models import UserModel


class Permissions:
    # User
    USER_CREATE  = "user.create"
    USER_READ    = "user.read"
    USER_UPDATE  = "user.update"
    USER_DELETE  = "user.delete"

    # Role
    ROLE_CREATE  = "role.create"
    ROLE_READ    = "role.read"
    ROLE_UPDATE  = "role.update"
    ROLE_DELETE  = "role.delete"
    ROLE_ASSIGN  = "role.assign"
    ROLE_REVOKE  = "role.revoke"

    #Permission
    PERMISSION_CREATE  = "role.create"
    PERMISSION_READ    = "role.read"
    PERMISSION_UPDATE  = "role.update"
    PERMISSION_DELETE  = "role.delete"
    PERMISSION_ASSIGN  = "role.assign"

def has_permission(user: UserModel, codename: str) -> bool:
    if not user:
        return False
    if user.phone_number == settings.GOD:
        return True
    return any(
        role_permission.codename == codename
        for user_role in user.role
        for role_permission in user_role.role.permissions
    )


def permission(codename: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, data: dict, *args, **kwargs):
            try:
                requester_id = data.get("requested_by")
                if not requester_id:
                    return {"error": "requested_by is required"}

                from user_management.models import UserModel

                user = self.db.query(UserModel).filter_by(id=requester_id).first()

                if not has_permission(user, codename):
                    return {"error": f"forbidden: missing permission '{codename}'"}

                return func(self, data, *args, **kwargs)

            except Exception as e:
                logger.error(e)
                return {"error": str(e)}

        return wrapper
    return decorator