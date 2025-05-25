from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from backend.models.text import TextInput
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory="frontend/components")


@router.get("/", response_class=HTMLResponse)
async def get_interface(request: Request):
    return templates.TemplateResponse("text-input.html", {"request": request})


@router.post("/text")
async def process_text(input_data: TextInput):
    logger.info(f"Received request with text: {input_data.text}")
    return {"message": f"Text received: {input_data.text}"}
