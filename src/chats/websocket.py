from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Example in-memory chat mapping (chat_id -> [user1, user2])
# In real apps, you’d fetch this from DB
CHAT_DB = {"chat1": ["user1", "user2"], "chat2": ["user2", "user3"]}


class ConnectionManager:
    def __init__(self):
        # Map user_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Map chat_id -> list of user_ids
        self.active_chats: Dict[str, List[str]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected")

        # Automatically subscribe the user to their chats
        for chat_id, users in CHAT_DB.items():
            if user_id in users:
                if chat_id not in self.active_chats:
                    self.active_chats[chat_id] = users

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
                # Send to both sender and recipient
                await self.send_personal_message(json.dumps(message), user_id)


manager = ConnectionManager()


@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                # Expected message: {"chat_id": "chat1", "content": "Hello"}
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
