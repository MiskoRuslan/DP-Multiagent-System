from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from enum import Enum


class MessageType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class ChatMessageCreate(BaseModel):
    user_id: UUID
    agent_id: Optional[UUID]
    message_type: MessageType
    message_text: Optional[str] = None
    message_image: Optional[str] = None
    was_sent: datetime


class ChatMessageResponse(BaseModel):
    id: UUID
    user_id: UUID
    agent_id: Optional[UUID]
    message_type: MessageType
    message_text: Optional[str]
    message_image: Optional[str]
    was_sent: datetime
    sender: str

    class Config:
        from_attributes = True


class ChatQuery(BaseModel):
    user_id: UUID
    agent_id: UUID


class ClearChatRequest(BaseModel):
    user_id: str
    agent_id: str
