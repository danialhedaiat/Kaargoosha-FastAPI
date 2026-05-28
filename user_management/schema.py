from datetime import datetime

from pydantic import BaseModel, Field


class UserBaseSchema(BaseModel):


class UserCompleteSchema(UserBaseSchema):
    id: int
    is_verify: bool
    create_data: datetime
    phone_number: str = Field(..., max_length=15)
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)


class UserSocialMediaBaseSchema(BaseModel):
    social_media: str = Field(..., max_length=50)
    user_id: int


class UserSocialMediaResponseSchema(UserSocialMediaBaseSchema):
    id: int


class RoleBaseSchema(BaseModel):
    name: str = Field(..., max_length=30)




class RoleResponseSchema(RoleBaseSchema):
    id: int


class UserRoleBaseSchema(BaseModel):
    user_id: int
    role_id: int
