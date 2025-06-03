from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.models.user import User
from backend.config.database import SessionLocal


class UserManager:

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, email: str) -> Optional[User]:
        try:
            user = User(email=email)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            return None
        except Exception as e:
            self.db.rollback()
            raise e

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_all_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        return self.db.query(User).offset(offset).limit(limit).all()

    def update_user_email(self, user_id: str, new_email: str) -> Optional[User]:
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None

            user.email = new_email
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            return None
        except Exception as e:
            self.db.rollback()
            raise e

    def delete_user(self, user_id: str) -> bool:
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            self.db.delete(user)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def user_exists(self, email: str) -> bool:
        return self.db.query(User).filter(User.email == email).first() is not None

    def count_users(self) -> int:
        return self.db.query(User).count()


def get_user_manager() -> UserManager:
    db = SessionLocal()
    return UserManager(db)


class UserManagerContext:

    def __enter__(self) -> UserManager:
        self.db = SessionLocal()
        self.user_manager = UserManager(self.db)
        return self.user_manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
