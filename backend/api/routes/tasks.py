from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import base64
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import asyncio
from sqlalchemy.orm import Session

from backend.clients.weather_client import WeatherClient
from backend.core.managers.chat_manager import ChatManager, get_chat_manager
from backend.models.chat_history import ChatHistory, MessageType as DBMessageType
from backend.schemas.chat import MessageResponse, ChatMessage, MessageType
from backend.utils.helpers import get_db

router = APIRouter()
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)


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
    Asynchronous Message Treatment with Crewai
    """
    try:
        agent = create_chat_agent()
        task = create_chat_task(message, user_id, agent_id)

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, crew.kickoff)

        return str(result)

    except Exception as e:
        print(f"Error processing with CrewAI: {str(e)}")
        return f"Вибачте, сталася помилка при обробці вашого повідомлення: {str(e)}"


@router.post("/send", response_model=MessageResponse)
async def base_send(
        chat_message: ChatMessage,
        db: Session = Depends(get_db),
        chat_manager: ChatManager = Depends(get_chat_manager),
):

    weather_client = WeatherClient()
    city = "London"
    print(f"Current weather in {city}")
    print(weather_client.get_current_weather(city))
    print(f"\n\nForecast weather in {city}")
    print(weather_client.get_forecast(city=city, days=7))
    print(f"\n\nAstronomy in {city}")
    print(weather_client.get_astronomy(city))

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

    try:
        user_message_db = ChatHistory(
            user_id=chat_message.user_id,
            agent_id=chat_message.agent_id,
            message_type=DBMessageType.TEXT
            if chat_message.message_type == MessageType.TEXT
            else DBMessageType.IMAGE,
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

    if chat_message.message_type == MessageType.TEXT and chat_message.text:

        start_memory_prompt = ("THIS IS A SYSTEM PROMPT. PAST MESSAGE "
                               "HISTORY WILL NOW BE TRANSMITTED TO GIVE YOU CONTEXT:")

        end_memory_prompt = "PAST MESSAGE HISTORY COMPLETED"

        previous_messages = chat_manager.get_chat_by_user_and_agent(
            user_id=chat_message.user_id,
            agent_id=chat_message.agent_id
        )

        message_to_llm = ""
        message_to_llm += start_memory_prompt
        for previous_message in previous_messages:
            message_to_llm += "\n"
            message_to_llm += f"Sender: {previous_message.sender}\n"
            message_to_llm += f"Message: {previous_message.message_text}\n"
        message_to_llm += end_memory_prompt

        try:
            ai_response = await process_with_crewai(
                message_to_llm,
                chat_message.user_id,
                chat_message.agent_id
            )
            print(f"AI Response: {ai_response}")

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
                print("The agent's response is saved in the database")
            except Exception as e:
                print(f"Failed to Save Agent Answer: {str(e)}")
                db.rollback()

        except Exception as e:
            print(f"Error generating AI response: {str(e)}")
            ai_response = "Sorry, failed to generate the answer to your message."

    elif chat_message.message_type == MessageType.IMAGE:
        ai_response = ("Image received. Image processing "
                       "will be added in future versions.")

        try:
            agent_message_db = ChatHistory(
                user_id=chat_message.user_id,
                agent_id=chat_message.agent_id,
                message_type=DBMessageType.TEXT,
                sender="AGENT",
                message_text=ai_response,
                was_sent=datetime.utcnow()
            )
            db.add(agent_message_db)
            db.commit()
        except Exception as e:
            print(f"Помилка збереження відповіді про зображення: {str(e)}")
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
