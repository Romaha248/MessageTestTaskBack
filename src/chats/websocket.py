import json
import logging
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from src.chats.service import get_chat_members
from src.database.dbcore import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.message_history: Dict[UUID, List[dict]] = {}  # per chat history
        self.max_history = 50  # store up to 50 messages per chat

    async def connect(self, user_id: UUID, websocket: WebSocket):
        """Accept connection and register user."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(
            f"User {user_id} connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, user_id: UUID):
        """Remove user from connections."""
        self.active_connections.pop(user_id, None)
        logger.info(
            f"User {user_id} disconnected. Remaining connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, user_id: UUID, message: dict):
        """Send message to a specific user if online."""
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send personal message to {user_id}: {e}")

    async def broadcast_to_chat(
        self, chat_id: UUID, sender_id: UUID, message: dict, db: Session
    ):
        participants = get_chat_members(db, chat_id)
        logger.info(f"Broadcasting to chat {chat_id} participants: {participants}")

        for user_id in participants:
            if user_id == sender_id:
                continue
            ws = self.active_connections.get(user_id)
            if ws:
                try:
                    await ws.send_json(message)
                    logger.info(f"✅ Sent to {user_id}")
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
            else:
                logger.info(f"❌ User {user_id} not connected")

    def store_message(self, chat_id: UUID, message: dict):
        """Keep a limited message history per chat."""
        if chat_id not in self.message_history:
            self.message_history[chat_id] = []
        self.message_history[chat_id].append(message)
        if len(self.message_history[chat_id]) > self.max_history:
            self.message_history[chat_id] = self.message_history[chat_id][
                -self.max_history :
            ]

    async def send_chat_history(self, websocket: WebSocket, chat_id: UUID):
        """Send previous messages to a user who just connected."""
        if chat_id in self.message_history:
            await websocket.send_json(
                {
                    "type": "history",
                    "messages": self.message_history[chat_id],
                }
            )


connection_manager = ConnectionManager()


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: UUID, db: Session = Depends(get_db)
):
    """Main WebSocket handler for user messaging."""
    await connection_manager.connect(user_id, websocket)
    try:
        while True:
            data_text = await websocket.receive_text()

            try:
                data = json.loads(data_text)
                chat_id = UUID(data["chat_id"])
                content = data["content"]
            except (KeyError, ValueError, json.JSONDecodeError):
                await websocket.send_json(
                    {"type": "error", "message": "Invalid message format"}
                )
                continue

            message = {
                "type": "message",
                "chat_id": str(chat_id),
                "sender_id": str(user_id),
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Store message
            connection_manager.store_message(chat_id, message)

            # Send confirmation to sender
            await connection_manager.send_personal_message(user_id, message)

            # Broadcast to chat participants
            await connection_manager.broadcast_to_chat(
                chat_id, sender_id=user_id, message=message, db=db
            )

    except WebSocketDisconnect:
        connection_manager.disconnect(user_id)
        logger.info(f"WebSocket disconnected: {user_id}")
    except Exception as e:
        logger.error(f"Unexpected WebSocket error ({user_id}): {e}")
        connection_manager.disconnect(user_id)
