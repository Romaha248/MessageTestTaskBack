from fastapi import APIRouter, Depends, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status
from typing import Annotated
from src.dependency import DbSession
from src.auth.schemas import RegisterUserRequest, Tokens
from src.auth.service import create_user, login


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def register_user(db: DbSession, register_user_request: RegisterUserRequest):
    user = create_user(db, register_user_request)
    return {"id": user.id, "email": user.email, "username": user.username}


@router.post("/login", status_code=status.HTTP_200_OK, response_model=Tokens)
async def login_for_tokens(
    db: DbSession,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
):
    return login(db, form_data, response)
