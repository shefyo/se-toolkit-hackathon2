import os
import json
import re
from typing import List, Dict
from openai import OpenAI

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")


ADVISOR_SYSTEM_PROMPT = """You are a professional financial advisor specializing in personal finance.
Analyze the user's expense data and provide exactly 3 short, actionable financial tips.
Each tip should be specific, practical, and directly related to the spending patterns shown.

Format your response as a JSON array of exactly 3 objects:
[
  {"tip": "Your first tip here"},
  {"tip": "Your second tip here"},
  {"tip": "Your third tip here"}
]

Keep each tip to 1-2 sentences maximum. Be direct and actionable.
Return ONLY valid JSON, nothing else."""


def generate_financial_advice(expenses: List[Dict], stats: Dict) -> List[Dict]:
    """Generate financial advice based on user's expenses."""
    if not LLM_API_KEY:
        return _fallback_advice(expenses, stats)

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    # Build context from expenses
    total = stats.get("total", 0)
    by_category = stats.get("by_category", {})

    context = f"Total spending: ${total:.2f}\n"
    context += "Spending by category:\n"
    for cat, amount in by_category.items():
        context += f"  - {cat}: ${amount:.2f}\n"

    if expenses:
        context += "\nRecent expenses:\n"
        for exp in expenses[:20]:
            context += f"  - {exp['item']}: ${exp['amount']:.2f} ({exp['category']})\n"

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": ADVISOR_SYSTEM_PROMPT},
                {"role": "user", "content": context}
            ],
            temperature=0.7,
            max_tokens=500
        )

        content = response.choices[0].message.content.strip()

        # Extract JSON
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            tips = json.loads(json_match.group())
            return tips if isinstance(tips, list) else []

        return []
    except Exception as e:
        print(f"Advice generation error: {e}")
        return _fallback_advice(expenses, stats)


def _fallback_advice(expenses: List[Dict], stats: Dict) -> List[Dict]:
    """Generate basic advice without LLM."""
    total = stats.get("total", 0)
    by_category = stats.get("by_category", {})

    tips = []

    if total > 0:
        tips.append(f"Your total spending is ${total:.2f}. Consider setting a monthly budget to track your expenses.")

    if by_category:
        top_category = max(by_category, key=by_category.get)
        top_amount = by_category[top_category]
        tips.append(f"Your highest spending category is '{top_category}' at ${top_amount:.2f}. Look for ways to reduce costs in this area.")

    if len(by_category) > 2:
        tips.append(f"You spend across {len(by_category)} categories. Review if all these expenses align with your financial goals.")
    else:
        tips.append("Track all your expenses consistently to get better insights into your spending habits.")

    # Ensure exactly 3 tips
    default_tips = [
        "Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings.",
        "Set up an emergency fund with at least 3 months of expenses.",
        "Review your subscriptions and cancel ones you don't use regularly.",
        "Consider cooking at home more often to save on food expenses.",
        "Use cashback apps or loyalty programs for regular purchases."
    ]

    while len(tips) < 3:
        for default in default_tips:
            if default not in tips:
                tips.append(default)
                break

    return [{"tip": tip} for tip in tips[:3]]
