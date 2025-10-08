from pydantic import BaseModel, EmailStr
from uuid import UUID


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    new_password_confirm: str
