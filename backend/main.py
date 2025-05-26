import os
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.api.routes.text import router as text_router
from backend.api.routes.agents import router as agent_router
from backend.api.routes.tasks import router as task_router
from backend.api.routes.chats import router as chat_router
from backend.utils.logging import setup_logging
from backend.config.database import SessionLocal
from backend.core.managers.user_manager import UserManager


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
current_dir = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(current_dir, "..", "frontend", "components"))


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

app.include_router(text_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")

current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "..", "frontend", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})
