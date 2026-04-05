import os
import sys
import time
import logging
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# Track users in chat mode
chat_mode_users = set()

# Category emoji map
CATEGORY_EMOJIS = {
    "food": "🍔",
    "transport": "🚕",
    "entertainment": "🎬",
    "shopping": "🛍️",
    "utilities": "💡",
    "health": "🏥",
    "travel": "✈️",
    "other": "📦",
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _emoji(category: str) -> str:
    return CATEGORY_EMOJIS.get(category, "📦")


def wait_for_backend(max_retries: int = 10, delay: int = 2) -> bool:
    """Block until backend /health responds or max_retries exhausted."""
    health_url = f"{BACKEND_URL}/health"
    for i in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(health_url)
                if resp.status_code == 200:
                    logger.info("Backend is healthy — starting bot")
                    return True
        except Exception:
            pass
        logger.info("Waiting for backend… (%d/%d)", i, max_retries)
        time.sleep(delay)
    logger.error("Backend did not become healthy after %d retries — proceeding anyway", max_retries)
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome_message = (
        "👋 Welcome to *SmartReceipt*!\n\n"
        "I'm your AI-powered financial assistant.\n\n"
        "*Commands:*\n"
        "• Send expenses — I'll parse & log them automatically\n"
        "• /stats — View your spending analytics\n"
        "• /advice — Get AI-powered financial tips\n"
        "• /chat — Chat with me about your finances\n"
        "• /exit — Exit chat mode\n\n"
        "*Example:*\n"
        "_coffee 5, pizza 10, cinema ticket 20_"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command — show spending analytics."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/stats")
            response.raise_for_status()
            data = response.json()

        total = data.get("total", 0)
        by_category = data.get("by_category", {})
        expense_count = data.get("expense_count", 0)

        message = f"📊 *Spending Analytics*\n\n"
        message += f"Total expenses: {expense_count}\n"
        message += f"Total spending: *${total:.2f}*\n\n"

        if by_category:
            message += "*By category:*\n"
            for cat, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                emoji = _emoji(cat)
                message += f"{emoji} {cat}: ${amount:.2f}\n"
        else:
            message += "No expenses recorded yet. Send me your expenses to get started!"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        await update.message.reply_text(
            "⚠️ Sorry, I encountered an error fetching your stats. Please try again later."
        )


async def advice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /advice command — get AI financial tips."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/advice")
            response.raise_for_status()
            data = response.json()

        tips = data.get("tips", [])

        if not tips:
            await update.message.reply_text(
                "🤔 I need more expense data to provide personalized advice. "
                "Start logging your expenses!"
            )
            return

        message = "💡 *Financial Tips:*\n\n"
        for i, tip_data in enumerate(tips, 1):
            tip = tip_data.get("tip", "")
            message += f"{i}. {tip}\n\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error fetching advice: {e}")
        await update.message.reply_text(
            "⚠️ Sorry, I encountered an error generating advice. Please try again later."
        )


async def chat_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chat command — enter chat mode with AI assistant."""
    user_id = update.effective_user.id
    chat_mode_users.add(user_id)

    await update.message.reply_text(
        "💬 *Chat Mode Activated*\n\n"
        "You can now ask me questions about your finances.\n"
        "Examples:\n"
        "• Where do I spend the most?\n"
        "• How can I save money?\n"
        "• What's my total spending?\n\n"
        "Send /exit to leave chat mode.",
        parse_mode="Markdown",
    )


async def exit_chat_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /exit command — exit chat mode."""
    user_id = update.effective_user.id
    chat_mode_users.discard(user_id)

    await update.message.reply_text(
        "👋 Exited chat mode. Send /chat to start chatting again."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id in chat_mode_users:
        await handle_chat_message(update, user_text)
    else:
        await handle_expense_message(update, user_text)


async def handle_chat_message(update: Update, user_text: str):
    """Handle message in chat mode — send to /chat endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={"message": user_text},
            )
            response.raise_for_status()
            data = response.json()

        bot_response = data.get("response", "")

        if bot_response:
            await update.message.reply_text(bot_response)
        else:
            await update.message.reply_text(
                "⚠️ Sorry, I couldn't process that. Try asking about your spending or budget."
            )

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        await update.message.reply_text(
            "⚠️ Sorry, I encountered an error. Please try again."
        )


async def handle_expense_message(update: Update, user_text: str):
    """Handle expense message — send to /parse-expenses endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/parse-expenses",
                json={"text": user_text},
            )
            response.raise_for_status()
            data = response.json()

        saved_expenses = data.get("saved", [])

        if not saved_expenses:
            await update.message.reply_text(
                "❌ No expenses found in your message. Try something like:\n"
                "_coffee 5, pizza 10, cinema ticket 20_",
                parse_mode="Markdown",
            )
            return

        message = "✅ *Saved:*\n\n"
        for exp in saved_expenses:
            item = exp["item"]
            amount = exp["amount"]
            category = exp["category"]
            emoji = _emoji(category)
            message += f"• {item} — ${amount:.2f} ({category} {emoji})\n"

        total = sum(exp["amount"] for exp in saved_expenses)
        message += f"\n💰 Total: ${total:.2f}"

        await update.message.reply_text(message, parse_mode="Markdown")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error processing expense: {e.response.status_code} - {e.response.text}")
        await update.message.reply_text(
            "⚠️ Server error. Please try again in a moment."
        )
    except Exception as e:
        logger.error(f"Error processing expense: {e}")
        await update.message.reply_text(
            "⚠️ Sorry, I encountered an error processing your expenses. Please try again."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by Updates."""
    logger.warning(f"Update {update} caused error: {context.error}")


def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN not set. Please set the environment variable."
        )
        return

    # Wait for backend to be healthy before starting
    wait_for_backend(max_retries=10, delay=2)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("advice", advice))
    app.add_handler(CommandHandler("chat", chat_mode))
    app.add_handler(CommandHandler("exit", exit_chat_mode))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot is running…")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
