from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from src.database.dbcore import get_db
from src.chats.service import get_user_chats  # returns list of Chats objects

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        # user_id -> WebSocket
        self.active_connections: Dict[UUID, WebSocket] = {}
        # chat_id -> list of user_ids
        self.active_chats: Dict[UUID, List[UUID]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket, db: Session):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"✅ User {user_id} connected")

        # Register all chats this user belongs to
        user_chats = get_user_chats(db, user_id)
        for chat in user_chats:
            participants = [chat.user1_id, chat.user2_id]
            self.active_chats[chat.id] = participants

        print(f"Active chats now: {self.active_chats}")

    def disconnect(self, user_id: UUID):
        if user_id in self.active_connections:
            self.active_connections.pop(user_id)
            print(f"❌ User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: UUID):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_text(json.dumps(message))

    async def send_message_to_chat(self, chat_id: UUID, message: dict, sender_id: UUID):
        users = self.active_chats.get(chat_id, [])
        print(f"📤 Sending message to chat {chat_id}: {users}")

        payload = {
            "event": "message_new",
            "chat_id": str(chat_id),
            "sender_id": str(sender_id),
            "content": message["content"],
            "message_id": str(message["id"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        for user_id in users:
            ws = self.active_connections.get(user_id)
            if ws:
                await ws.send_text(json.dumps(payload))

    async def send_message_deleted(
        self,
        chat_id: UUID,
        message_id: UUID,
    ):
        """Notify all chat members that a message was deleted."""
        users = self.active_chats.get(chat_id, [])
        print(f"🗑️ Deleting message {message_id} in chat {chat_id}")

        payload = {
            "event": "message_deleted",
            "chat_id": str(chat_id),
            "message_id": str(message_id),
        }

        for user_id in users:
            ws = self.active_connections.get(user_id)
            if ws:
                await ws.send_text(json.dumps(payload))


manager = ConnectionManager()


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: UUID, db: Session = Depends(get_db)
):
    await manager.connect(user_id, websocket, db)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                chat_id = UUID(data.get("chat_id"))
                content = data.get("content")
                event_type = data.get("event")

                if not chat_id or not content:
                    await manager.send_personal_message(
                        {"error": "Invalid message format"}, user_id
                    )
                    continue

                if event_type == "message_new":
                    content = data.get("content")
                    await manager.send_message_to_chat(
                        chat_id, {"content": content}, sender_id=user_id
                    )

                # 🗑️ Message delete event (optional if you want to handle delete via WS too)
                elif event_type == "message_delete":
                    message_id = UUID(data.get("message_id"))
                    await manager.send_message_deleted(chat_id, message_id)
                # Echo message to all chat participants (including sender)
                # await manager.send_message_to_chat(
                #     chat_id, {"content": content}, sender_id=user_id
                # )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"error": "Invalid JSON format"}, user_id
                )

    except WebSocketDisconnect:
        manager.disconnect(user_id)
