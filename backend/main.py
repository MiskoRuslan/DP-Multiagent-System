from fastapi import FastAPI, Depends, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from backend.api.routes.text import router as text_router
from backend.core.managers.agent_manager import AgentManager, get_agent_manager
from backend.utils.logging import setup_logging
from backend.config.database import SessionLocal
from backend.core.managers.user_manager import UserManager


templates = Jinja2Templates(directory="frontend/components")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_manager(db: Session = Depends(get_db)) -> UserManager:
    return UserManager(db)


setup_logging()
app = FastAPI()


app.include_router(text_router, prefix="/api")
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return templates.TemplateResponse("text-input.html", {"request": request})


@app.get("/all_users", response_model=List[dict])
async def get_all_users(
        limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
        offset: int = Query(0, ge=0, description="Number of users to miss"),
        user_manager: UserManager = Depends(get_user_manager)
):
    users = user_manager.get_all_users(limit=limit, offset=offset)
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        for user in users
    ]


@app.get("/all_agents", response_model=List[dict])
async def get_all_users(
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