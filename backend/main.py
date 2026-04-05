from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging

logger = logging.getLogger("smartreceipt")

# ==================== SAFE DB IMPORT ====================

try:
    from backend.database import (
        init_db,
        add_expense,
        get_all_expenses,
        get_recent_expenses,
        get_total_spending,
        get_expenses_by_category,
        save_advice,
        get_advice_history,
        save_chat_message,
        get_chat_history,
    )
except Exception as e:
    logger.error(f"Database module import failed: {e}")
    # Provide no-op stubs so the app still starts
    def _safe_noop(*args, **kwargs):
        return [] if "list" in str(type(None)) else {}

    init_db = lambda: None
    add_expense = lambda *a, **kw: {}
    get_all_expenses = lambda: []
    get_recent_expenses = lambda *a, **kw: []
    get_total_spending = lambda: 0.0
    get_expenses_by_category = lambda: {}
    save_advice = lambda *a, **kw: {}
    get_advice_history = lambda *a, **kw: []
    save_chat_message = lambda *a, **kw: {}
    get_chat_history = lambda *a, **kw: []

try:
    from backend.llm_parser import parse_expenses_with_llm
except Exception as e:
    logger.error(f"LLM parser import failed: {e}")
    parse_expenses_with_llm = lambda text: []

try:
    from backend.llm_advisor import generate_financial_advice
except Exception as e:
    logger.error(f"LLM advisor import failed: {e}")
    generate_financial_advice = lambda *a, **kw: []

try:
    from backend.llm_chat import chat_with_assistant
except Exception as e:
    logger.error(f"LLM chat import failed: {e}")
    chat_with_assistant = lambda *a, **kw: "Sorry, the AI assistant is temporarily unavailable."

# ==================== APP ====================

app = FastAPI(title="SmartReceipt API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== REQUEST MODELS ====================

class ParseRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    message: str


# ==================== HEALTH — ROOT LEVEL, NO DB DEPS ====================

@app.get("/health")
async def health():
    """Health check — no DB, no LLM, always responds."""
    return {"status": "ok", "version": "2.0.0"}


# ==================== STARTUP ====================

@app.on_event("startup")
def startup():
    """Initialize DB safely — never crashes the app."""
    try:
        # Ensure data directory exists before DB init
        os.makedirs("data", exist_ok=True)
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"DB init error (app will continue): {e}")


# ==================== API ROUTER (mounted at /api) ====================

api = FastAPI()


@api.get("/health")
async def api_health():
    """Health check via /api/health (through nginx proxy)."""
    return {"status": "ok", "version": "2.0.0"}


# --- Expense endpoints ---

@api.post("/parse-expenses")
async def parse_expenses(request: ParseRequest):
    """Parse expenses from text using LLM and save to database."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        expenses = parse_expenses_with_llm(request.text)
    except Exception as e:
        logger.error(f"LLM parsing error: {e}")
        return {"message": "⚠️ Parser temporarily unavailable. Please try again.", "saved": []}

    if not expenses:
        return {"message": "No expense found in the text.", "saved": []}

    saved = []
    for exp in expenses:
        try:
            item = exp.get("item", "Unknown")
            amount = float(exp.get("amount", 0))
            category = exp.get("category", "other")

            if amount <= 0:
                continue

            saved_expense = add_expense(item, amount, category)
            saved.append(saved_expense)
        except (ValueError, TypeError, Exception) as e:
            logger.error(f"Error saving expense: {e}")
            continue

    items = ", ".join(e["item"] for e in saved)
    return {"message": f"✅ Saved {len(saved)} expense(s): {items}", "saved": saved}


@api.get("/expenses")
async def get_expenses():
    """Get all stored expenses."""
    try:
        return get_all_expenses()
    except Exception as e:
        logger.error(f"Error fetching expenses: {e}")
        return []


# --- Stats ---

@api.get("/stats")
async def get_stats():
    """Get spending analytics: total and per-category."""
    try:
        total = get_total_spending()
        by_category = get_expenses_by_category()
        expenses = get_all_expenses()

        return {
            "total": total,
            "by_category": by_category,
            "expense_count": len(expenses)
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {"total": 0.0, "by_category": {}, "expense_count": 0}


# --- Advice ---

@api.get("/advice")
async def get_advice():
    """Generate AI financial advice based on user's expenses."""
    try:
        expenses = get_recent_expenses(limit=50)
        total = get_total_spending()
        by_category = get_expenses_by_category()

        stats = {"total": total, "by_category": by_category}
        tips = generate_financial_advice(expenses, stats)

        if not tips:
            tips = [{"tip": "Start tracking your expenses regularly to build a spending history for better insights."}]

        # Save advice to history (non-critical)
        try:
            advice_content = "\n".join([t["tip"] for t in tips])
            save_advice(advice_content)
        except Exception:
            pass

        return {"tips": tips, "saved": True}
    except Exception as e:
        logger.error(f"Error generating advice: {e}")
        return {"tips": [{"tip": "AI advice is temporarily unavailable. Please try again later."}], "saved": False}


@api.get("/advice/history")
async def get_advice_history_endpoint(limit: int = 10):
    """Get advice history."""
    try:
        return get_advice_history(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching advice history: {e}")
        return []


# --- Chat ---

@api.post("/chat")
async def chat(request: ChatRequest):
    """Chat with AI financial assistant."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        expenses = get_recent_expenses(limit=30)
        chat_hist = get_chat_history(limit=10)
        total = get_total_spending()
        by_category = get_expenses_by_category()

        stats = {"total": total, "by_category": by_category}

        bot_response = chat_with_assistant(
            user_message=request.message,
            expenses=expenses,
            chat_history=chat_hist,
            stats=stats
        )

        # Save chat message (non-critical)
        try:
            save_chat_message(request.message, bot_response)
        except Exception:
            pass

        return {"response": bot_response, "saved": True}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"response": "Sorry, the chat assistant is temporarily unavailable.", "saved": False}


@api.get("/chat/history")
async def get_chat_history_endpoint(limit: int = 20):
    """Get chat history."""
    try:
        history = get_chat_history(limit=limit)
        return list(reversed(history))
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        return []


# Mount API under /api prefix
app.mount("/api", api)


# ==================== WEB FRONTEND (served at /) ====================

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_frontend():
        """Serve the web frontend."""
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
