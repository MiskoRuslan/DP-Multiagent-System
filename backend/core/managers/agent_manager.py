from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.core.agents.sky_agent import OpenSkyAviationAgent
from backend.core.agents.sky_analyst_agent import AviationAnalysisAgent
from backend.core.agents.windy_agent import WindyWeatherAgent
from backend.models.agents import Agent
from backend.config.database import SessionLocal
from backend.core.agents.weather_agent import SmartWeatherAgent
from backend.core.agents.generic_agent import GenericAgent


class AgentManager:
    def __init__(self, db: Session):
        self.db = db
        self.agents = {
            "weather": SmartWeatherAgent,
            "generic": GenericAgent,
            "windy": WindyWeatherAgent,
            "opensky": OpenSkyAviationAgent,
            "sky_analysis": AviationAnalysisAgent
        }

    def create_agent(self, name: str, system_prompt: Optional[str] = None, agent_type: str = "Generic") -> Optional[Agent]:
        try:
            agent = Agent(name=name, system_prompt=system_prompt, agent_type=agent_type)
            self.db.add(agent)
            self.db.commit()
            self.db.refresh(agent)
            return agent
        except IntegrityError:
            self.db.rollback()
            return None
        except Exception as e:
            self.db.rollback()
            raise e

    def get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        return self.db.query(Agent).filter(Agent.id == agent_id).first()

    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        return self.db.query(Agent).filter(Agent.name == name).first()

    def get_all_agents(self, limit: int = 100, offset: int = 0) -> List[Agent]:
        return self.db.query(Agent).offset(offset).limit(limit).all()

    def update_agent_sp(self, agent_id: str, system_prompt: str) -> Optional[Agent]:
        try:
            agent = self.get_agent_by_id(agent_id)
            if not agent:
                return None
            agent.system_prompt = system_prompt
            self.db.commit()
            self.db.refresh(agent)
            return agent
        except IntegrityError:
            self.db.rollback()
            return None
        except Exception as e:
            self.db.rollback()
            raise e

    def delete_agent(self, agent_id: str) -> bool:
        try:
            agent = self.get_agent_by_id(agent_id)
            if not agent:
                return False
            self.db.delete(agent)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def agent_exists(self, name: str) -> bool:
        return self.db.query(Agent).filter(Agent.name == name).first() is not None

    def count_agents(self) -> int:
        return self.db.query(Agent).count()

    def get_agent_instance(self, agent_id: str):
        db_agent = self.get_agent_by_id(agent_id)
        if not db_agent:
            return None
        if db_agent.agent_type in self.agents:
            return self.agents[db_agent.agent_type](agent_id, db_agent.name, db_agent.system_prompt)
        return None


def get_agent_manager() -> AgentManager:
    db = SessionLocal()
    return AgentManager(db)


class UserManagerContext:
    def __enter__(self) -> AgentManager:
        self.db = SessionLocal()
        self.user_manager = AgentManager(self.db)
        return self.user_manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()