from fastapi import APIRouter, Depends, Response, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status
from src.dependency import DbSession
from src.chats.service import (
    get_all_user_chat,
    get_all_messages_for_chat,
    create_chat,
    create_message,
    delete_message_by_id,
)
from src.auth.service import CurrentUser
from src.chats.schemas import MessageRequest
from src.chats.websocket import manager


router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/all-messages")
async def get_all_messages(
    db: DbSession,
    current_user: CurrentUser,
    chat_id: str = Query(..., description="Chat ID to fetch messages for"),
):
    messages = get_all_messages_for_chat(
        db, chat_id=chat_id, current_user_id=current_user.user_id
    )
    return messages


@router.get("/all-chats")
async def get_all_chats(
    db: DbSession,
    current_user: CurrentUser,
):
    chats = get_all_user_chat(db, current_user.user_id)
    return chats


@router.post("/create-chat")
async def create_users_chat(
    db: DbSession,
    current_user: CurrentUser,
    user2_id: str = Query(..., description="User ID to create chat"),
):
    return create_chat(db, user1_id=current_user.user_id, user2_id=user2_id)


@router.post("/create-message")
async def create_user_message(
    message_request: MessageRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    return create_message(db, message_request)


@router.delete("/delete-message/{id}")
async def delete_message(
    db: DbSession,
    current_user: CurrentUser,
    id: str,
):
    chat_id = delete_message_by_id(db, id)

    await manager.send_message_deleted(chat_id, id)

    return {"success": True}
