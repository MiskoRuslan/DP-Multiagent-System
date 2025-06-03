from fastapi import APIRouter, Depends
from typing import List
from backend.core.managers.chat_manager import ChatManager, get_chat_manager
from backend.schemas.chat import ChatMessageCreate, ChatMessageResponse, \
    ClearChatRequest

router = APIRouter()


@router.post("/add_message", response_model=ChatMessageResponse)
async def add_message(
    message_data: ChatMessageCreate,
    chat_manager: ChatManager = Depends(get_chat_manager),
):
    new_message = chat_manager.add_message(**message_data.dict())
    return new_message


@router.get("/get_chat", response_model=List[ChatMessageResponse])
async def get_chat(
    user_id: str,
    agent_id: str,
    chat_manager: ChatManager = Depends(get_chat_manager),
):
    chat = chat_manager.get_chat_by_user_and_agent(
        user_id=user_id,
        agent_id=agent_id
    )
    return chat


@router.post("/clear_chat")
async def clear_chat(
    request: ClearChatRequest,
    chat_manager: ChatManager = Depends(get_chat_manager),
):
    result = chat_manager.clear_chat_history(
        user_id=request.user_id,
        agent_id=request.agent_id
    )
    return result
