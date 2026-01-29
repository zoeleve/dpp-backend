from pydantic import BaseModel, EmailStr, ConfigDict
from app.configs.roles import Role, UserSubRole
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: Role = Role.USER
    subrole: Optional[UserSubRole] = None
    is_active: bool = True


class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[Role] = None
    subrole: Optional[UserSubRole] = None
    is_active: Optional[bool] = None


class PasswordUpdate(BaseModel):
    new_password: str
