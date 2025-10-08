from pydantic import BaseModel
from uuid import UUID


class ChatResponse(BaseModel):
    id: UUID
    user1_id: UUID
    user2_id: UUID


class MessageRequest(BaseModel):
    chat_id: UUID
    sender_id: UUID
    content: str


class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    sender_id: UUID
    content: str
