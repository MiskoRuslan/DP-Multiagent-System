import uuid
from datetime import datetime
from sqlalchemy import Column, Enum, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.config.database import Base
import enum


class MessageType(enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    message_type = Column(Enum(MessageType), nullable=False)
    message_text = Column(String, nullable=True)
    message_image = Column(String, nullable=True)
    was_sent = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="chat_history")
    agent = relationship("Agent", backref="chat_history")
