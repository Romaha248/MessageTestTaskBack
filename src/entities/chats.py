from src.database.dbcore import Base
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    func,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid


class Chats(Base):
    __tablename__ = "chats"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )

    user1_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user2_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user1 = relationship("Users", foreign_keys=[user1_id])
    user2 = relationship("Users", foreign_keys=[user2_id])
    messages = relationship("Messages", back_populates="chat", cascade="all, delete")

    __table_args__ = (
        Index("ix_messages_id_created_at", "id", "created_at"),
        UniqueConstraint("user1_id", "user2_id", name="unique_chat_pair"),
    )
