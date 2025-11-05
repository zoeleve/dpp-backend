from sqlalchemy import Column, Integer, String, Enum
from pydantic import BaseModel
from app.db.database_postgre import Base
from app.configs.roles import Role, UserSubRole


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.USER, nullable=False)
    subrole = Column(Enum(UserSubRole), nullable=True)  # "admin", "technician", "manufacturer"


class LoginRequest(BaseModel):
    username: str
    password: str