# Multiagent LLM System

A simple FastAPI-based application with a web interface for text input and API processing.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Docker (optional)

### Installation & Setup

#### Option 1: Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**
   ```bash
   uvicorn backend.main:app --reload
   ```

#### Option 2: Docker

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

### Access the Application

Open your browser and navigate to: **http://localhost:8000**

- Enter your text in the input field
- Click "Send" to process your request
- View the response from the system

## 📁 Project Structure

```
multiagent-llm-system/
├── backend/                 # FastAPI backend
│   ├── main.py             # Main application file
│   ├── models/             # Data models
│   └── routes/             # API endpoints
├── frontend/               # Web interface
│   ├── index.html          # Main HTML file
│   ├── style.css           # Styling
│   └── script.js           # Frontend logic
├── docker-compose.yml      # Docker configuration
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🛠️ Development

The application runs in development mode with auto-reload enabled when using the `--reload` flag with uvicorn.

## 📝 API Documentation

Once the application is running, you can access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc