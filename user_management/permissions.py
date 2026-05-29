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
