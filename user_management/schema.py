from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class UserBaseSchema(BaseModel):
    phone_number: str = Field(..., max_length=15)
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)


class UserSocialMediaBaseSchema(BaseModel):
    social_media: str = Field(..., max_length=50)
    username: str = Field(..., max_length=50)
    user_id: int


class UserSocialMediaResponseSchema(UserSocialMediaBaseSchema):
    id: int

    class Config:
        from_attributes = True


class UserWithoutRoleSchema(UserBaseSchema):
    id: int
    is_verify: bool
    create_date: datetime
    social_media: List[UserSocialMediaResponseSchema] = []


class RoleBaseSchema(BaseModel):
    name: str = Field(..., max_length=30)


class RoleResponseSchema(RoleBaseSchema):
    id: int

    class Config:
        from_attributes = True


class AssignRoleBaseSchema(BaseModel):
    user: UserWithoutRoleSchema
    role: RoleResponseSchema


class AssignRoleSchema(AssignRoleBaseSchema):
    requested_by: int


class AssignRoleResponseSchema(AssignRoleBaseSchema):
    id: int

    class Config:
        from_attributes = True


class RevokeRoleBaseSchema(BaseModel):
    user_id: int
    role_id: int


class RevokeRoleSchema(RevokeRoleBaseSchema):
    requested_by: int


class RolePermissionBaseSchema(BaseModel):
    codename: str = Field(..., )
    role_id: int
    role: RoleResponseSchema


class RolePermissionResponseSchema(RolePermissionBaseSchema):
    id: int

    class Config:
        from_attributes = True


class UserCompleteSchema(UserBaseSchema):
    id: int
    is_verify: bool
    create_date: datetime
    social_media: List[UserSocialMediaResponseSchema] = []
    role_permission: List[AssignRoleResponseSchema] = []

    class Config:
        from_attributes = True
