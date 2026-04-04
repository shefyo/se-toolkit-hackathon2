from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os

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
from backend.llm_parser import parse_expenses_with_llm
from backend.llm_advisor import generate_financial_advice
from backend.llm_chat import chat_with_assistant

app = FastAPI(title="SmartReceipt API", version="2.0.0")

# CORS for frontend
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


# ==================== RESPONSE MODELS ====================

class StatsResponse(BaseModel):
    total: float
    by_category: dict
    expense_count: int


class AdviceResponse(BaseModel):
    tips: List[dict]
    saved: bool


class ChatResponse(BaseModel):
    response: str
    saved: bool


# ==================== EVENTS ====================

@app.on_event("startup")
def startup():
    init_db()


# ==================== EXPENSE ENDPOINTS ====================

@app.post("/parse-expenses")
async def parse_expenses(request: ParseRequest):
    """Parse expenses from text using LLM and save to database."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    expenses = parse_expenses_with_llm(request.text)

    if not expenses:
        return {"message": "No expenses found in the text.", "saved": []}

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
        except (ValueError, TypeError) as e:
            print(f"Error saving expense: {e}")
            continue

    return {"message": f"Saved {len(saved)} expense(s)", "saved": saved}


@app.get("/expenses")
async def get_expenses():
    """Get all stored expenses."""
    return get_all_expenses()


# ==================== STATS ENDPOINT ====================

@app.get("/stats")
async def get_stats():
    """Get spending analytics: total and per-category."""
    total = get_total_spending()
    by_category = get_expenses_by_category()
    expenses = get_all_expenses()

    return StatsResponse(
        total=total,
        by_category=by_category,
        expense_count=len(expenses)
    ).model_dump()


# ==================== ADVICE ENDPOINT ====================

@app.get("/advice")
async def get_advice():
    """Generate AI financial advice based on user's expenses."""
    expenses = get_recent_expenses(limit=50)
    total = get_total_spending()
    by_category = get_expenses_by_category()

    stats = {
        "total": total,
        "by_category": by_category
    }

    tips = generate_financial_advice(expenses, stats)

    if not tips:
        tips = [{"tip": "Start tracking your expenses regularly to build a spending history for better insights."}]

    # Save advice to history
    advice_content = "\n".join([t["tip"] for t in tips])
    saved_record = save_advice(advice_content)

    return AdviceResponse(
        tips=tips,
        saved=True
    ).model_dump()


@app.get("/advice/history")
async def get_advice_history_endpoint(limit: int = 10):
    """Get advice history."""
    return get_advice_history(limit=limit)


# ==================== CHAT ENDPOINT ====================

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with AI financial assistant."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    expenses = get_recent_expenses(limit=30)
    chat_hist = get_chat_history(limit=10)
    total = get_total_spending()
    by_category = get_expenses_by_category()

    stats = {
        "total": total,
        "by_category": by_category
    }

    bot_response = chat_with_assistant(
        user_message=request.message,
        expenses=expenses,
        chat_history=chat_hist,
        stats=stats
    )

    # Save chat message
    save_chat_message(request.message, bot_response)

    return ChatResponse(
        response=bot_response,
        saved=True
    ).model_dump()


@app.get("/chat/history")
async def get_chat_history_endpoint(limit: int = 20):
    """Get chat history."""
    history = get_chat_history(limit=limit)
    return list(reversed(history))  # Return in chronological order


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}


# ==================== WEB FRONTEND ====================

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
