import json
import logging
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections, message history, and broadcasts."""

    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.chat_participants: Dict[UUID, List[UUID]] = {}  # chat_id -> user_ids
        self.message_history: Dict[UUID, List[dict]] = {}  # chat_id -> messages
        self.max_history = 50

    # ----------------- Connection Handling -----------------
    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(
            f"User {user_id} connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, user_id: UUID):
        self.active_connections.pop(user_id, None)
        logger.info(
            f"User {user_id} disconnected. Remaining connections: {len(self.active_connections)}"
        )

    # ----------------- Chat Participant Handling -----------------
    def register_chat(self, chat_id: UUID, participants: List[UUID]):
        """Register chat participants in memory."""
        self.chat_participants[chat_id] = participants
        logger.info(f"Registered chat {chat_id} participants: {participants}")

    # ----------------- Message History -----------------
    def store_message(self, chat_id: UUID, message: dict):
        if chat_id not in self.message_history:
            self.message_history[chat_id] = []
        self.message_history[chat_id].append(message)
        # Keep only last `max_history` messages
        if len(self.message_history[chat_id]) > self.max_history:
            self.message_history[chat_id] = self.message_history[chat_id][
                -self.max_history :
            ]

    async def send_chat_history(self, websocket: WebSocket, chat_id: UUID):
        if chat_id in self.message_history:
            await websocket.send_json(
                {"type": "history", "messages": self.message_history[chat_id]}
            )

    # ----------------- Messaging -----------------
    async def send_personal_message(self, user_id: UUID, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send personal message to {user_id}: {e}")

    async def broadcast_to_chat(self, chat_id: UUID, sender_id: UUID, message: dict):
        participants = self.chat_participants.get(chat_id, [])
        logger.info(
            f"Broadcasting message in chat {chat_id} to participants: {participants}"
        )
        logger.info(f"Active connections: {list(self.active_connections.keys())}")

        for user_id in participants:
            if user_id == sender_id:
                continue
            ws = self.active_connections.get(user_id)
            if ws:
                try:
                    await ws.send_json(message)
                    logger.info(f"✅ Sent to {user_id}")
                except Exception as e:
                    logger.error(f"Error sending to {user_id}: {e}")
            else:
                logger.info(f"❌ User {user_id} not connected")


# ----------------- Global Connection Manager -----------------
connection_manager = ConnectionManager()


# ----------------- WebSocket Endpoint -----------------
@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: UUID):
    """
    WebSocket handler for messaging.
    Expects messages in JSON format: {"chat_id": "...", "content": "..."}
    """
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

            # Store in memory
            connection_manager.store_message(chat_id, message)

            # Send confirmation to sender
            await connection_manager.send_personal_message(user_id, message)

            # Broadcast to other chat participants
            await connection_manager.broadcast_to_chat(
                chat_id, sender_id=user_id, message=message
            )

    except WebSocketDisconnect:
        connection_manager.disconnect(user_id)
        logger.info(f"WebSocket disconnected: {user_id}")
    except Exception as e:
        logger.exception(f"Unexpected WebSocket error ({user_id}): {e}")
        connection_manager.disconnect(user_id)
