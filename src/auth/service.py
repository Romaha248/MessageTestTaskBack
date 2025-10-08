import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from src.auth.schemas import RegisterUserRequest, TokenData, Tokens
from src.entities.users import Users
import logging
from starlette import status
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import jwt
from jwt import InvalidTokenError
from uuid import UUID
from typing import Annotated
from fastapi import Depends, HTTPException, Response


load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("ALGORITHM")
JWT_ACCESS_TOKEN_TTL = int(os.getenv("JWT_ACCESS_TOKEN_TTL"))

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/login")

if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET not set in environment")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logging.error(f"Password verification failed: {e}")
        return False


def create_access_token(
    email: str,
    user_id: UUID,
    username: str,
    expires_days: int = JWT_ACCESS_TOKEN_TTL,
) -> str:

    try:
        expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
        payload = {
            "sub": email,
            "id": str(user_id),
            "username": username,
            "exp": expire,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    except Exception as e:
        logging.error(f"Failed to create access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token",
        )


def verify_token(token: str) -> TokenData:

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")
        username: str = payload.get("username")
        if not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )
        return TokenData(user_id=user_id, username=username)
    except InvalidTokenError as e:
        logging.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )


def create_user(
    db: Session, register_user_request: RegisterUserRequest
) -> RegisterUserRequest:

    try:
        existing_email = (
            db.query(Users).filter(Users.email == register_user_request.email).first()
        )

        if existing_email:
            logging.warning(
                f"Registration failed: Email already exists: {register_user_request.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        existing_username = (
            db.query(Users)
            .filter(Users.username == register_user_request.username)
            .first()
        )

        if existing_username:
            logging.warning(
                f"Registration failed: Username already exists: {register_user_request.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

        create_user_model = Users(
            email=register_user_request.email,
            username=register_user_request.username,
            password=get_password_hash(register_user_request.password),
        )
        db.add(create_user_model)
        db.commit()
        db.refresh(create_user_model)

        logging.info(f"Successfully registered user: {register_user_request.email}")
        return create_user_model

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to register user {register_user_request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )


def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]) -> TokenData:
    return verify_token(token)


CurrentUser = Annotated[TokenData, Depends(get_current_user)]


def login(
    db: Session,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
) -> Tokens:

    user = db.query(Users).filter(Users.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        logging.warning(
            f"Failed authentication attempt for email: {form_data.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wrong email or pass",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user."
        )

    try:
        access_token = create_access_token(user.email, user.id, user.username)

        return Tokens(access_token=access_token, token_type="bearer")
    except Exception as e:
        logging.error(f"Failed during login token creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error",
        )
