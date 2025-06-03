from fastapi import APIRouter, Depends, Query
from typing import List
from backend.core.managers.agent_manager import AgentManager, get_agent_manager

router = APIRouter()


@router.get("/all_agents", response_model=List[dict])
async def get_all_agents(
    limit: int = Query(100, ge=1, le=1000, description="Number of agents to return"),
    offset: int = Query(0, ge=0, description="Number of agents to miss"),
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    agents = agent_manager.get_all_agents(limit=limit, offset=offset)
    return [
        {
            "id": str(agent.id),
            "name": agent.name,
            "system_prompt": agent.system_prompt if agent.system_prompt else None
        }
        for agent in agents
    ]
