# src/chats/websocket.py
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
from datetime import datetime
import json
from uuid import UUID
from src.chats.service import get_chat_members
from sqlalchemy.orm import Session
from src.database.dbcore import get_db


class ConnectionManager:
    def __init__(self):
        # map user_id to WebSocket
        self.active_connections: Dict[UUID, WebSocket] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: UUID):
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, user_id: UUID, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast_to_chat(
        self, chat_id: UUID, sender_id: UUID, message: dict, db: Session
    ):
        # get all participants of the chat
        participants = get_chat_members(db, chat_id)
        for user_id in participants:
            if user_id == sender_id:
                continue
            ws = self.active_connections.get(user_id)
            if ws:
                await ws.send_json(message)


connection_manager = ConnectionManager()


# WebSocket endpoint
from fastapi import APIRouter

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: UUID, db: Session = Depends(get_db)
):
    await connection_manager.connect(user_id, websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                # expected: { "chat_id": str, "content": str }
                chat_id = data["chat_id"]
                content = data["content"]
            except (KeyError, json.JSONDecodeError):
                await websocket.send_json({"error": "Invalid message format"})
                continue

            message = {
                "chat_id": chat_id,
                "sender_id": user_id,
                "content": content,
                "timestamp": datetime.now(datetime.timezone.utc),
            }

            # send back to sender (optional)
            await connection_manager.send_personal_message(user_id, message)
            # broadcast to other participants
            await connection_manager.broadcast_to_chat(
                chat_id, sender_id=user_id, message=message, db=db
            )

    except WebSocketDisconnect:
        connection_manager.disconnect(user_id)
        # Optionally notify other participants that user left
