from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from backend.models.text import TextInput
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Modern FastAPI Text Interface</title>
    <link rel="stylesheet" href="/static/css/main.css">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500">
    <div class="bg-white bg-opacity-90 p-8 rounded-2xl shadow-2xl w-full max-w-lg backdrop-blur-md">
        <h1 class="text-3xl font-bold mb-6 text-center text-gray-800">Text Input Interface</h1>
        <div class="mb-6">
            <input type="text" id="textInput" class="w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all" placeholder="Enter your text...">
        </div>
        <button onclick="sendText()" class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-3 rounded-lg hover:from-purple-700 hover:to-indigo-700 transition-all duration-300 transform hover:scale-105">Send</button>
        <p id="response" class="mt-6 text-center text-gray-600">...</p>
    </div>
    <script src="/static/js/api.js"></script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def get_interface():
    return HTML_CONTENT


@router.post("/text")
async def process_text(input_data: TextInput):
    logger.info(f"Received request with text: {input_data.text}")
    return {"message": f"Text received: {input_data.text}"}
