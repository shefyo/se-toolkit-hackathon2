# 🧾 SmartReceipt

AI-powered expense tracker with Telegram bot and web interface.

## Features

- 🤖 **Telegram Bot** - Log expenses via chat messages
- 🌐 **Web Interface** - Simple UI for expense tracking
- 🧠 **AI Parsing** - Automatic expense extraction and categorization using LLM
- 💾 **SQLite Database** - Lightweight, zero-config storage

## Architecture

```
SmartReceipt/
├── backend/
│   ├── main.py          # FastAPI application
│   ├── database.py      # SQLite database layer
│   └── llm_parser.py    # LLM expense parsing
├── bot/
│   └── telegram_bot.py  # Telegram bot implementation
├── frontend/
│   └── index.html       # Web interface
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- Telegram account (to create a bot)
- OpenAI API key (optional, for AI parsing)

### 2. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to name your bot
4. Copy the **bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`)

### 3. Install Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install packages
pip install -r requirements.txt
```

### 4. Environment Variables

Create a `.env` file or export environment variables:

```bash
# Telegram Bot Token (required for bot functionality)
export TELEGRAM_BOT_TOKEN="your-bot-token-here"

# OpenAI API Key (optional - falls back to regex parser if not set)
export LLM_API_KEY="your-openai-api-key"

# Optional: Custom LLM endpoint (for compatible APIs)
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-3.5-turbo"
```

### 5. Run the Application

#### Start the Backend Server

```bash
cd /mnt/c/Users/Oleg/Desktop/set/se-toolkit-lab-9
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`

#### Start the Telegram Bot (in a separate terminal)

```bash
cd /mnt/c/Users/Oleg/Desktop/set/se-toolkit-lab-9
export BACKEND_URL="http://localhost:8000"
python -m bot.telegram_bot
```

### 6. Access the Interfaces

- **Web Interface**: Open `http://localhost:8000` in your browser
- **Telegram Bot**: Open your bot in Telegram and send `/start`

## Usage

### Via Telegram Bot

1. Open your bot in Telegram
2. Send a message like:
   ```
   I bought coffee for 5 and pizza for 10
   ```
3. The bot will reply:
   ```
   ✅ Saved:
   
   • coffee: 5 (food)
   • pizza: 10 (food)
   ```

### Via Web Interface

1. Open `http://localhost:8000`
2. Enter expenses in the textarea
3. Click "Parse & Save Expenses"
4. View your expense history below

## API Endpoints

### POST /parse-expenses

Parse and save expenses from text.

**Request:**
```json
{
  "text": "I bought coffee for 5 and pizza for 10"
}
```

**Response:**
```json
{
  "message": "Saved 2 expense(s)",
  "saved": [
    {
      "id": 1,
      "item": "coffee",
      "amount": 5.0,
      "category": "food",
      "created_at": "2024-01-01T12:00:00"
    },
    {
      "id": 2,
      "item": "pizza",
      "amount": 10.0,
      "category": "food",
      "created_at": "2024-01-01T12:00:01"
    }
  ]
}
```

### GET /expenses

Get all stored expenses.

**Response:**
```json
[
  {
    "id": 1,
    "item": "coffee",
    "amount": 5.0,
    "category": "food",
    "created_at": "2024-01-01T12:00:00"
  }
]
```

## LLM Integration

The system uses OpenAI-compatible APIs for expense parsing. You can use:

- **OpenAI** (default): Set `LLM_API_KEY` and optionally `LLM_BASE_URL`
- **Local LLMs**: Point `LLM_BASE_URL` to local endpoints (e.g., Ollama, LM Studio)
- **Fallback**: Without an API key, a simple regex-based parser is used

### Categories

The LLM categorizes expenses into:
- food
- transport
- entertainment
- shopping
- utilities
- health
- travel
- other

## Database

SQLite database (`smartreceipt.db`) is created automatically on first run.

**Schema:**
```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Troubleshooting

- **Bot not responding**: Ensure `TELEGRAM_BOT_TOKEN` is set correctly
- **LLM errors**: Check `LLM_API_KEY` or use the fallback parser
- **Port conflicts**: Change port in the uvicorn command if 8000 is in use
