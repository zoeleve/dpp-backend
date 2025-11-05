from pydantic import BaseModel, EmailStr
from app.configs.roles import Role, UserSubRole
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: Role = Role.USER
    subrole: Optional[UserSubRole] = None


class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[Role] = None
    subrole: Optional[UserSubRole] = None


class PasswordUpdate(BaseModel):
    new_password: str
