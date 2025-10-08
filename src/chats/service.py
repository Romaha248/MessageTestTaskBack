from src.chats.schemas import ChatResponse, MessageRequest, MessageResponse
from src.entities.chats import Chats
from src.entities.messages import Messages
import logging
from starlette import status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID
from fastapi import HTTPException
from uuid import UUID


def get_all_user_chat(db: Session, user_id: UUID) -> list[ChatResponse]:
    try:
        chats = (
            db.query(Chats)
            .filter(or_(Chats.user1_id == user_id, Chats.user2_id == user_id))
            .all()
        )

        if not chats:
            logging.info(f"No chats found for user: {user_id}")
            return []

        logging.info(f"Retrieved {len(chats)} chats for user: {user_id}")
        return chats

    except Exception as e:
        logging.error(f"Error retrieving chats for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chats.",
        )


def get_all_messages_for_chat(
    db: Session, chat_id: UUID, current_user_id: UUID
) -> list[MessageResponse]:
    try:
        chat = db.query(Chats).filter(Chats.id == chat_id).first()

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found.",
            )

        messages = db.query(Messages).filter(Messages.chat_id == chat_id).all()

        if not messages:
            logging.info(f"No messages found for chat: {chat_id}")
            return []

        logging.info(f"Retrieved {len(messages)} messages for chat: {chat_id}")
        return messages

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving messages for chat {chat_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages.",
        )


def create_chat(db: Session, user1_id: UUID, user2_id: UUID) -> ChatResponse:
    try:
        chat = (
            db.query(Chats)
            .filter(Chats.user1_id == user1_id)
            .filter(Chats.user2_id == user2_id)
            .first()
        )

        if chat:
            logging.warning(f"Chat creating failed: Chat already exists: {chat.id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat already exists",
            )

        new_chat = Chats(user1_id=user1_id, user2_id=user2_id)

        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)

        logging.info(f"Successfully creating chat: {new_chat.id}")
        return new_chat

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to create chat : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat",
        )


def create_message(db: Session, message_request: MessageRequest) -> MessageResponse:
    try:
        new_message = Messages(
            chat_id=message_request.chat_id,
            sender_id=message_request.sender_id,
            content=message_request.content,
        )

        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        logging.info(f"Message created successfully in chat {message_request.chat_id}")

        return new_message

    except Exception as e:
        logging.error(f"Error creating message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create message.",
        )


def get_user_chats(db: Session, user_id: UUID) -> list[Chats]:
    try:
        chats = (
            db.query(Chats)
            .filter((Chats.user1_id == user_id) | (Chats.user2_id == user_id))
            .all()
        )

        return chats

    except Exception as e:
        logging.error(f"Error retrieving chats for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chats.",
        )
