import os
import json
import re
from typing import List
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


SYSTEM_PROMPT = """You are an expense extraction assistant. 
Extract all expenses from the user's text and return them as a JSON array.
Each expense should have:
- item: the name of the item (string)
- amount: the cost (number)
- category: a category like "food", "transport", "entertainment", "utilities", "shopping", etc. (string)

Return ONLY valid JSON, nothing else. No markdown, no explanation.

Example output:
[
  {"item": "coffee", "amount": 5, "category": "food"},
  {"item": "pizza", "amount": 10, "category": "food"}
]"""


def extract_expenses(text: str) -> List[dict]:
    """Use LLM to extract expenses from free-form text."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            expenses = json.loads(json_match.group())
            return expenses
        
        return []
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return []
