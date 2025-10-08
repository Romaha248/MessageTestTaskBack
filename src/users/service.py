from src.users.schemas import UserResponse, PasswordChange
from src.entities.users import Users
from src.auth.service import get_password_hash, verify_password
from sqlalchemy.orm import Session
from starlette import status
from uuid import UUID
from fastapi import HTTPException
import logging
from sqlalchemy.ext.asyncio import AsyncSession


def get_user_by_id(db: Session, user_id: UUID) -> Users:

    try:
        user = db.query(Users).filter(Users.id == user_id).first()

        if not user:
            logging.warning(f"User not found with ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        logging.info(f"Successfully retrieved user with ID: {user_id}")
        return user

    except Exception as e:
        logging.error(f"Error retrieving user with ID {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user.",
        )


def change_pass(db: Session, user_id: UUID, change_pass: PasswordChange) -> None:

    try:
        user = get_user_by_id(db, user_id)

        if not verify_password(change_pass.current_password, user.password):
            logging.warning(f"Invalid current password for user ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid current password.",
            )

        if verify_password(change_pass.new_password, user.password):
            logging.warning(f"New password same as old password for user ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="New password cannot be the same as the old password.",
            )

        if change_pass.new_password != change_pass.new_password_confirm:
            logging.warning(f"Password confirmation mismatch for user ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match.",
            )

        try:
            user.password = get_password_hash(change_pass.new_password)
        except Exception as e:
            logging.error(f"Failed to hash password for user ID {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password.",
            )

        db.commit()

        logging.info(f"Password successfully changed for user ID: {user_id}")

    except HTTPException:
        raise
    except Exception as e:
        logging.error(
            f"Unexpected error during password change for user ID {user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password due to server error.",
        )


def get_all_users_from_db(db: Session, user_id: UUID) -> list[Users]:
    try:
        users = db.query(Users).filter(Users.id != user_id).all()

        if not users:
            logging.warning(f"No users found in the database.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        logging.info(f"Successfully retrieved {len(users)} users.")
        return users

    except Exception as e:
        logging.error(f"Error retrieving users : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user.",
        )
