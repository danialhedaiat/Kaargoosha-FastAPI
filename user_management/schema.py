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


class UserCompleteSchema(UserBaseSchema):
    id: int
    is_verify: bool
    create_date: datetime
    user_social_medias: List[UserSocialMediaResponseSchema] = []

    class Config:
        from_attributes = True


class RoleBaseSchema(BaseModel):
    name: str = Field(..., max_length=30)


class RoleResponseSchema(RoleBaseSchema):
    id: int

    class Config:
        from_attributes = True


class AssignRoleBaseSchema(BaseModel):
    user_id: int
    role_id: int


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
