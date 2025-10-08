from pydantic import BaseModel, EmailStr, Field, field_validator
from uuid import UUID
import re


class RegisterUserRequest(BaseModel):
    email: EmailStr
    username: str = Field(
        min_length=6,
        max_length=30,
        description="Username should be between 6 and 30 chars",
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password should be between 8 and 128 chars",
    )

    @field_validator("username")
    @classmethod
    def username_allowed_chars(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, and underscores"
            )
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class Tokens(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str | None = None
    username: str

    def get_uuid(cls) -> UUID | None:
        if cls.user_id:
            return UUID(cls.user_id)
        return None
