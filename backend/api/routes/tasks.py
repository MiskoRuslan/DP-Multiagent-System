from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
import base64

router = APIRouter()


class MessageType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class ChatMessage(BaseModel):
    message_type: MessageType
    text: Optional[str] = None
    image: Optional[str] = None
    was_sent: datetime
    agent_id: str
    user_id: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ChatMessageResponse(BaseModel):
    message_type: str
    text: Optional[str] = None
    image: Optional[str] = None
    was_sent: str
    agent_id: str
    user_id: str


@router.post("/send", response_model=ChatMessageResponse)
async def base_send(chat_message: ChatMessage):
    print("Received message:")
    print(f"Message Type: {chat_message.message_type}")
    print(f"Text: {chat_message.text}")
    if chat_message.image:
        try:
            base64.b64decode(chat_message.image)
            print(f"Image: [Base64-encoded image data]")
        except Exception as e:
            print(f"Image: Invalid base64 string - {str(e)}")
    else:
        print(f"Image: None")
    print(f"Was Sent: {chat_message.was_sent}")
    print(f"Agent ID: {chat_message.agent_id}")
    print(f"User ID: {chat_message.user_id}")

    response = ChatMessageResponse(
        message_type=str(chat_message.message_type),
        text=str(chat_message.text) if chat_message.text is not None else None,
        image=str(chat_message.image) if chat_message.image is not None else None,
        was_sent=chat_message.was_sent.isoformat(),
        agent_id=str(chat_message.agent_id),
        user_id=str(chat_message.user_id)
    )

    return response
