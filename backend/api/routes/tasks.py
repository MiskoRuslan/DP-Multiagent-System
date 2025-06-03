from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import base64
from sqlalchemy.orm import Session
from backend.clients.weather_client import WeatherClient
from backend.core.managers.chat_manager import ChatManager, get_chat_manager
from backend.core.managers.agent_manager import AgentManager, get_agent_manager
from backend.models.chat_history import ChatHistory, MessageType as DBMessageType
from backend.schemas.chat import MessageResponse, ChatMessage, MessageType
from backend.utils.helpers import get_db

router = APIRouter()


async def process_with_agent(message: str, user_id: str, agent_id: str,
                             agent_manager: AgentManager) -> str:
    try:
        agent_instance = agent_manager.get_agent_instance(agent_id)
        if not agent_instance:
            return "Помилка: Агент не знайдено або неправильно налаштовано"

        # Дочекатися результату асинхронного методу
        return await agent_instance.process_message(message)
    except Exception as e:
        print(f"Помилка обробки з агентом: {str(e)}")
        return f"Вибачте, сталася помилка при обробці вашого повідомлення: {str(e)}"


@router.post("/send", response_model=MessageResponse)
async def base_send(
        chat_message: ChatMessage,
        db: Session = Depends(get_db),
        chat_manager: ChatManager = Depends(get_chat_manager),
        agent_manager: AgentManager = Depends(get_agent_manager),
):
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

        ai_response = None

        if chat_message.message_type == MessageType.TEXT and chat_message.text:
            start_memory_prompt = (
                "ЦЕ СИСТЕМНИЙ ПРОМПТ. ІСТОРІЯ ПОВІДОМЛЕНЬ ТЕПЕР БУДЕ ПЕРЕДАНА ДЛЯ НАДАННЯ КОНТЕКСТУ:")
            end_memory_prompt = "ІСТОРІЯ ПОВІДОМЛЕНЬ ЗАВЕРШЕНА"
            previous_messages = chat_manager.get_chat_by_user_and_agent(
                user_id=chat_message.user_id,
                agent_id=chat_message.agent_id
            )
            message_to_llm = f"{start_memory_prompt}\n"
            for previous_message in previous_messages:
                message_to_llm += f"Відправник: {previous_message.sender}\n"
                message_to_llm += f"Повідомлення: {previous_message.message_text}\n"
            message_to_llm += f"{end_memory_prompt}\nПоточне повідомлення: {chat_message.text}"

            try:
                # Дочекатися результату від process_with_agent
                ai_response = await process_with_agent(
                    message_to_llm,
                    chat_message.user_id,
                    chat_message.agent_id,
                    agent_manager
                )

                try:
                    agent_message_db = ChatHistory(
                        user_id=chat_message.user_id,
                        agent_id=chat_message.agent_id,
                        message_type=DBMessageType.TEXT,
                        sender="AGENT",
                        message_text=ai_response,
                        was_sent=datetime.now() + timedelta(hours=3)
                    )
                    db.add(agent_message_db)
                    db.commit()
                except Exception as e:
                    print(f"Не вдалося зберегти відповідь агента: {str(e)}")
                    db.rollback()

            except Exception as e:
                print(f"Помилка генерації відповіді AI: {str(e)}")
                ai_response = "Вибачте, не вдалося згенерувати відповідь на ваше повідомлення."

        elif chat_message.message_type == MessageType.IMAGE:
            ai_response = (
                "Зображення отримано. Обробка зображень буде додана в майбутніх версіях.")

            try:
                agent_message_db = ChatHistory(
                    user_id=chat_message.user_id,
                    agent_id=chat_message.agent_id,
                    message_type=DBMessageType.TEXT,
                    sender="AGENT",
                    message_text=ai_response,
                    was_sent=datetime.now() + timedelta(hours=3)
                )
                db.add(agent_message_db)
                db.commit()
            except Exception as e:
                print(f"Не вдалося зберегти відповідь про зображення: {str(e)}")
                db.rollback()

        response = MessageResponse(
            message_type=str(chat_message.message_type),
            text=str(chat_message.text) if chat_message.text is not None else None,
            image=str(chat_message.image) if chat_message.image is not None else None,
            was_sent=chat_message.was_sent.isoformat(),
            agent_id=str(chat_message.agent_id),
            user_id=str(chat_message.user_id),
            ai_response=ai_response
        )

        return response
    except Exception as e:
        print(f"Помилка в base_send: {str(e)}")
        raise