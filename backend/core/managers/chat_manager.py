import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.models.chat_history import ChatHistory
from backend.config.database import SessionLocal


class ChatManager:

    def __init__(self, db: Session):
        self.db = db

    def add_message(
            self,
            user_id: str,
            message_type: str,
            was_sent: datetime,
            message_text: str = None,
            message_image: str = None,
            agent_id: str = None,
    ) -> Optional[ChatHistory]:
        try:
            message = ChatHistory(
                id=uuid.uuid4(),
                user_id=user_id,
                message_type=message_type,
                was_sent=was_sent,
                message_text=message_text,
                message_image=message_image,
                agent_id=agent_id,
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            return message
        except IntegrityError:
            self.db.rollback()
            return None
        except Exception as e:
            self.db.rollback()
            raise e

    def get_chat_by_user_and_agent(
            self,
            user_id: str,
            agent_id: str
    ) -> List[ChatHistory]:
        return self.db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.agent_id == agent_id
        ).order_by(ChatHistory.was_sent).all()

    def clear_chat_history(self, user_id: str, agent_id: str) -> bool:
        try:
            self.db.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.agent_id == agent_id
            ).delete()
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            return False


def get_chat_manager() -> ChatManager:
    db = SessionLocal()
    return ChatManager(db)


class ChatManagerContext:

    def __enter__(self) -> ChatManager:
        self.db = SessionLocal()
        self.chat_manager = ChatManager(self.db)
        return self.chat_manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
