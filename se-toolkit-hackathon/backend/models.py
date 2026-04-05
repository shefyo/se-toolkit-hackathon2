from pydantic import BaseModel
from typing import List, Optional


class ExpenseInput(BaseModel):
    text: str


class Expense(BaseModel):
    id: Optional[int] = None
    item: str
    amount: float
    category: str
    created_at: Optional[str] = None


class ExpenseList(BaseModel):
    expenses: List[Expense]
