from fastapi import APIRouter, status
from uuid import UUID
from src.users.schemas import UserResponse, PasswordChange
from src.dependency import DbSession
from src.auth.service import CurrentUser
from src.users.service import get_user_by_id, change_pass, get_all_users_from_db


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUser, db: DbSession):
    return get_user_by_id(db, current_user.get_uuid())


@router.get("/all")
async def get_all_users(current_user: CurrentUser, db: DbSession):
    return get_all_users_from_db(db, current_user.user_id)


@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_change: PasswordChange, db: DbSession, current_user: CurrentUser
):
    change_pass(db, current_user.get_uuid(), password_change)
    return {"message": "Password changed successfully."}
