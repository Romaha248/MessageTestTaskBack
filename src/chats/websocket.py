from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
from uuid import UUID

from sqlalchemy.orm import Session
from src.database.dbcore import get_db
from src.chats.service import (
    get_user_chats,
)  # This should return all chats for a user from DB

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        # chat_id -> list of user_ids
        self.active_chats: Dict[UUID, List[UUID]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket, db: Session):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected")

        # Fetch all chats for this user from DB
        user_chats = get_user_chats(db, user_id)  # Returns list of chat objects
        for chat in user_chats:
            participants = [
                chat.user1,
                chat.user2,
            ]  # assuming chat.users is a list of User objects
            self.active_chats[chat.id] = participants

    def disconnect(self, user_id: UUID):
        if user_id in self.active_connections:
            self.active_connections.pop(user_id)
            print(f"User {user_id} disconnected")

    async def send_personal_message(self, message: str, user_id: UUID):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(message)

    async def send_message_to_chat(self, chat_id: UUID, message: dict, sender_id: UUID):
        users = self.active_chats.get(chat_id, [])
        for user_id in users:
            if user_id in self.active_connections:
                await self.send_personal_message(json.dumps(message), user_id)


manager = ConnectionManager()


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: UUID, db: Session = Depends(get_db)
):
    await manager.connect(user_id, websocket, db)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                # Expected message: {"chat_id": "123", "content": "Hello"}
                message_data = json.loads(data)
                chat_id = message_data.get("chat_id")
                content = message_data.get("content")

                if chat_id and content:
                    message = {"from": user_id, "content": content}
                    await manager.send_message_to_chat(
                        chat_id, message, sender_id=user_id
                    )
                else:
                    await manager.send_personal_message(
                        "Invalid message format", user_id
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message("Invalid JSON format", user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
