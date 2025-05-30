import uuid
from sqlalchemy import Column, String, Float
from sqlalchemy.dialects.postgresql import UUID
from backend.config.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    system_prompt = Column(String, nullable=True)
    agent_type = Column(String, nullable=False, default="Generic")  # Generic\Specific
    temperature = Column(Float, nullable=False, default=0.8)
