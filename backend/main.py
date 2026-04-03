from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import os

from backend.database import init_db, add_expense, get_all_expenses
from backend.llm_parser import parse_expenses_with_llm

app = FastAPI(title="SmartReceipt API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ParseRequest(BaseModel):
    text: str


@app.on_event("startup")
def startup():
    init_db()


@app.post("/parse-expenses")
async def parse_expenses(request: ParseRequest):
    """Parse expenses from text using LLM and save to database."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Parse expenses using LLM
    expenses = parse_expenses_with_llm(request.text)

    if not expenses:
        return {"message": "No expenses found in the text.", "saved": []}

    # Save each expense to database
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


# Serve frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the web frontend."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
