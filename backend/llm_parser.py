import json
import os
from typing import List, Dict
from openai import OpenAI

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

SYSTEM_PROMPT = """You are an expense extraction assistant. 
Extract all expenses from the user's text and return ONLY a valid JSON array.
Each expense must have:
- item: the name of the expense
- amount: the numeric amount (number only, no currency symbols)
- category: one of [food, transport, entertainment, shopping, utilities, health, travel, other]

Return ONLY the JSON array, nothing else. If no expenses found, return [].

Example output:
[{"item": "coffee", "amount": 5, "category": "food"}, {"item": "pizza", "amount": 10, "category": "food"}]
"""


def parse_expenses_with_llm(text: str) -> List[Dict]:
    """Parse expenses from text using LLM."""
    if not LLM_API_KEY:
        # Fallback: simple regex-based extraction for testing without API key
        return _fallback_parse(text)

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=500
        )

        content = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        expenses = json.loads(content.strip())
        return expenses if isinstance(expenses, list) else []

    except Exception as e:
        print(f"LLM error: {e}, falling back to simple parsing")
        return _fallback_parse(text)


def _fallback_parse(text: str) -> List[Dict]:
    """Simple fallback parser that extracts items with amounts using regex."""
    import re
    
    # Split by "and" to handle multiple expenses
    parts = re.split(r'\s+and\s+', text, flags=re.IGNORECASE)
    
    expenses = []
    seen_items = set()
    
    for part in parts:
        part = part.strip()
        # Remove common prefixes
        part = re.sub(r'\b(bought|got|paid|spent|i|we|my|our)\s+', '', part, flags=re.IGNORECASE).strip()
        
        # Pattern: item "for" amount
        match = re.search(r'([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+for\s+(\d+(?:\.\d+)?)', part, re.IGNORECASE)
        if not match:
            # Pattern: amount then item
            match = re.search(r'(\d+(?:\.\d+)?)\s+(?:dollars?\s+)?(?:for\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+)?)', part, re.IGNORECASE)
            if match:
                amount, item = match.groups()
            else:
                continue
        else:
            item, amount = match.groups()
        
        item = item.strip().lower()
        # Skip common non-item words
        if item in ('and', 'the', 'a', 'an', 'for', 'my', 'some', 'also', 'then', 'with', 'i', 'we'):
            continue
        if item in seen_items:
            continue
        
        seen_items.add(item)
        expenses.append({
            "item": item,
            "amount": float(amount),
            "category": _guess_category(item)
        })
    
    return expenses


def _guess_category(item: str) -> str:
    """Simple category guessing based on item name."""
    food_items = ['coffee', 'pizza', 'food', 'lunch', 'dinner', 'breakfast', 'burger', 'snack', 'cake', 'beer', 'wine', 'drink', 'meal', 'restaurant', 'cafe', 'bakery']
    transport_items = ['taxi', 'uber', 'bus', 'train', 'metro', 'fuel', 'gas', 'parking', 'ticket']
    shopping_items = ['shirt', 'shoes', 'book', 'phone', 'laptop', 'clothes', 'gadget']
    health_items = ['medicine', 'doctor', 'pharmacy', 'hospital', 'gym', 'vitamin']
    
    item_lower = item.lower()
    
    for keyword in food_items:
        if keyword in item_lower:
            return 'food'
    for keyword in transport_items:
        if keyword in item_lower:
            return 'transport'
    for keyword in shopping_items:
        if keyword in item_lower:
            return 'shopping'
    for keyword in health_items:
        if keyword in item_lower:
            return 'health'
    
    return 'other'
