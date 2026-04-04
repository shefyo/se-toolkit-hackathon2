import os
import json
import re
from typing import List, Dict
from openai import OpenAI

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

MAX_CHAT_HISTORY = 10  # Number of recent messages for context


CHAT_SYSTEM_PROMPT = """You are SmartReceipt, an AI financial assistant.
You help users understand their spending, provide budgeting tips, and answer questions about their finances.
Be concise, friendly, and practical in your responses.
Keep responses under 3-4 sentences unless the user asks for detailed analysis.
If asked about something unrelated to finances, politely redirect the conversation back to money topics."""


def chat_with_assistant(
    user_message: str,
    expenses: List[Dict],
    chat_history: List[Dict],
    stats: Dict
) -> str:
    """Chat with the AI financial assistant, using expenses and chat history as context."""
    if not LLM_API_KEY:
        return _fallback_chat_response(user_message, expenses, stats)

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    # Build expense context
    context = "User's financial data:\n"
    context += f"Total spending: ${stats.get('total', 0):.2f}\n"

    by_category = stats.get("by_category", {})
    if by_category:
        context += "Spending by category:\n"
        for cat, amount in by_category.items():
            context += f"  - {cat}: ${amount:.2f}\n"

    if expenses:
        context += "\nRecent expenses:\n"
        for exp in expenses[:15]:
            context += f"  - {exp['item']}: ${exp['amount']:.2f} ({exp['category']})\n"
    else:
        context += "\nNo expenses recorded yet.\n"

    # Build messages with chat history
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT + "\n\n" + context}
    ]

    # Add recent chat history for conversation memory
    for msg in reversed(chat_history[:MAX_CHAT_HISTORY]):
        messages.append({"role": "assistant", "content": msg["bot_response"]})
        messages.append({"role": "user", "content": msg["user_message"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Chat error: {e}")
        return _fallback_chat_response(user_message, expenses, stats)


def _fallback_chat_response(user_message: str, expenses: List[Dict], stats: Dict) -> str:
    """Provide basic responses without LLM."""
    msg_lower = user_message.lower()

    total = stats.get("total", 0)
    by_category = stats.get("by_category", {})

    if "spend" in msg_lower or "most" in msg_lower:
        if by_category:
            top_cat = max(by_category, key=by_category.get)
            return f"You spend the most on '{top_cat}' (${by_category[top_cat]:.2f}). Consider reviewing if this aligns with your budget."
        return "No expenses recorded yet. Start tracking to get spending insights!"

    if "save" in msg_lower or "money" in msg_lower:
        return "Try setting a monthly budget, cutting unnecessary subscriptions, and cooking at home more often. Even small changes can add up significantly over time."

    if "total" in msg_lower or "how much" in msg_lower:
        return f"Your total spending is ${total:.2f}."

    if "budget" in msg_lower:
        return f"Based on your spending of ${total:.2f}, consider setting a monthly budget and tracking daily. The 50/30/20 rule (50% needs, 30% wants, 20% savings) is a good starting point."

    if "category" in msg_lower or "breakdown" in msg_lower:
        if by_category:
            breakdown = ", ".join([f"{k}: ${v:.2f}" for k, v in list(by_category.items())[:5]])
            return f"Your spending breakdown: {breakdown}."
        return "No category data available yet."

    if "tip" in msg_lower or "advice" in msg_lower:
        return "Track every expense, set realistic budgets, and review your spending weekly. Small consistent habits lead to big financial improvements."

    if "hello" in msg_lower or "hi" in msg_lower or "hey" in msg_lower:
        return "Hi! I'm your financial assistant. Ask me about your spending, budget tips, or how to save money."

    if "thank" in msg_lower:
        return "You're welcome! Feel free to ask anytime about your finances."

    return f"I can help you with spending insights, budgeting tips, and saving strategies. Your current total spending is ${total:.2f}. What would you like to know?"
