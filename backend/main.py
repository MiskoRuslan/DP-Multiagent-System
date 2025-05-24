from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from backend.api.routes.text import router as text_router
from backend.api.routes.text import HTML_CONTENT
from backend.utils.logging import setup_logging


setup_logging()
app = FastAPI()
app.include_router(text_router, prefix="/api")
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", response_class=HTMLResponse)
async def get_root():
    return HTML_CONTENT
