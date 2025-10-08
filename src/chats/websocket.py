from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from typing import Dict, List
import json

from sqlalchemy.orm import Session
from src.database.dbcore import get_db
from src.chats.service import (
    get_user_chats,
)  # This should return all chats for a user from DB

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        # chat_id -> list of user_ids
        self.active_chats: Dict[str, List[str]] = {}

    async def connect(self, user_id: str, websocket: WebSocket, db: Session):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected")

        # Fetch all chats for this user from DB
        user_chats = get_user_chats(db, user_id)  # Returns list of chat objects
        for chat in user_chats:
            chat_id = str(chat.id)
            participants = [
                str(u.id) for u in chat.users
            ]  # assuming chat.users is a list of User objects
            self.active_chats[chat_id] = participants

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            self.active_connections.pop(user_id)
            print(f"User {user_id} disconnected")

    async def send_personal_message(self, message: str, user_id: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(message)

    async def send_message_to_chat(self, chat_id: str, message: dict, sender_id: str):
        users = self.active_chats.get(chat_id, [])
        for user_id in users:
            if user_id in self.active_connections:
                await self.send_personal_message(json.dumps(message), user_id)


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: str, db: Session = Depends(get_db)
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
