from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum
import base64
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_openai import ChatOpenAI
import asyncio
from sqlalchemy.orm import Session

from backend.config.database import SessionLocal
from backend.models.chat_history import ChatHistory, MessageType as DBMessageType

router = APIRouter()

# Ініціалізація LLM (потрібно встановити OPENAI_API_KEY в змінних середовища)
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    ai_response: Optional[str] = None


# CrewAI Agent для обробки повідомлень
def create_chat_agent():
    return Agent(
        role='Chat Assistant',
        goal='Provide helpful and relevant responses to user messages',
        backstory="""You are a helpful AI assistant that processes user messages 
        and provides thoughtful, relevant responses. You should be friendly, 
        informative, and helpful in your interactions.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_chat_task(user_message: str, user_id: str, agent_id: str):
    return Task(
        description=f"""
        Process the following user message and provide an appropriate response:

        User Message: "{user_message}"
        User ID: {user_id}
        Agent ID: {agent_id}

        Provide a helpful, relevant, and friendly response to the user's message.
        Keep the response conversational and engaging.
        """,
        expected_output="A helpful and relevant response to the user's message",
        agent=create_chat_agent()
    )


async def process_with_crewai(message: str, user_id: str, agent_id: str) -> str:
    """
    Асинхронна обробка повідомлення за допомогою CrewAI
    """
    try:
        # Створення агента та задачі
        agent = create_chat_agent()
        task = create_chat_task(message, user_id, agent_id)

        # Створення команди
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )

        # Виконання задачі в окремому потоці для уникнення блокування
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, crew.kickoff)

        return str(result)

    except Exception as e:
        print(f"Error processing with CrewAI: {str(e)}")
        return f"Вибачте, сталася помилка при обробці вашого повідомлення: {str(e)}"


@router.post("/send", response_model=ChatMessageResponse)
async def base_send(chat_message: ChatMessage, db: Session = Depends(get_db)):
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

    ai_response = None

    # Зберегти повідомлення користувача в базу даних
    try:
        user_message_db = ChatHistory(
            user_id=chat_message.user_id,
            agent_id=chat_message.agent_id,
            message_type=DBMessageType.TEXT if chat_message.message_type == MessageType.TEXT else DBMessageType.IMAGE,
            sender="USER",
            message_text=chat_message.text,
            message_image=chat_message.image,
            was_sent=chat_message.was_sent + timedelta(hours=3)
        )
        db.add(user_message_db)
        db.commit()
        print("Повідомлення користувача збережено в БД")
    except Exception as e:
        print(f"Помилка збереження повідомлення користувача: {str(e)}")
        db.rollback()

    # Обробка текстового повідомлення за допомогою CrewAI
    if chat_message.message_type == MessageType.TEXT and chat_message.text:
        try:
            ai_response = await process_with_crewai(
                chat_message.text,
                chat_message.user_id,
                chat_message.agent_id
            )
            print(f"AI Response: {ai_response}")

            # Зберегти відповідь агента в базу даних
            try:
                agent_message_db = ChatHistory(
                    user_id=chat_message.user_id,
                    agent_id=chat_message.agent_id,
                    message_type=DBMessageType.TEXT,
                    sender="AGENT",
                    message_text=ai_response,
                    message_image=None,
                    was_sent=datetime.now() + timedelta(hours=3)
                )
                db.add(agent_message_db)
                db.commit()
                print("Відповідь агента збережена в БД")
            except Exception as e:
                print(f"Помилка збереження відповіді агента: {str(e)}")
                db.rollback()

        except Exception as e:
            print(f"Error generating AI response: {str(e)}")
            ai_response = "Вибачте, не вдалося згенерувати відповідь на ваше повідомлення."

    # Обробка зображень (поки що тільки логування)
    elif chat_message.message_type == MessageType.IMAGE:
        ai_response = "Отримано зображення. Обробка зображень буде додана в майбутніх версіях."

        # Зберегти відповідь про зображення в базу даних
        try:
            agent_message_db = ChatHistory(
                user_id=chat_message.user_id,
                agent_id=chat_message.agent_id,
                message_type=DBMessageType.TEXT,
                sender="AGENT",
                message_text=ai_response,
                message_image=None,
                was_sent=datetime.utcnow()
            )
            db.add(agent_message_db)
            db.commit()
        except Exception as e:
            print(f"Помилка збереження відповіді про зображення: {str(e)}")
            db.rollback()

    response = ChatMessageResponse(
        message_type=str(chat_message.message_type),
        text=str(chat_message.text) if chat_message.text is not None else None,
        image=str(chat_message.image) if chat_message.image is not None else None,
        was_sent=chat_message.was_sent.isoformat(),
        agent_id=str(chat_message.agent_id),
        user_id=str(chat_message.user_id),
        ai_response=ai_response
    )

    return response
