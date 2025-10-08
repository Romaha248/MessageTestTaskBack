from src.database.dbcore import Base
from sqlalchemy import Column, String, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid


class Users(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )

    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(30), unique=True, nullable=False)
    password = Column(String(128), nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sent_messages = relationship(
        "Messages", back_populates="sender", foreign_keys="Messages.sender_id"
    )

    __table_args__ = (Index("ix_users_email", "email"),)
