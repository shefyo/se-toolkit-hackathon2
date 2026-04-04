import os
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
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Track users in chat mode
chat_mode_users = set()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome_message = (
        "👋 Welcome to *SmartReceipt*!\n\n"
        "I'm your AI-powered financial assistant.\n\n"
        "*Commands:*\n"
        "• Send expenses — I'll log them automatically\n"
        "• /stats — View your spending analytics\n"
        "• /advice — Get AI-powered financial tips\n"
        "• /chat — Chat with me about your finances\n"
        "• /exit — Exit chat mode\n\n"
        "*Example expense:*\n"
        "_I bought coffee for 5 and pizza for 10_"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command — show spending analytics."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/stats")
            data = response.json()

        total = data.get("total", 0)
        by_category = data.get("by_category", {})
        expense_count = data.get("expense_count", 0)

        message = f"📊 *Spending Analytics*\n\n"
        message += f"Total expenses: {expense_count}\n"
        message += f"Total spending: *${total:.2f}*\n\n"

        if by_category:
            message += "*By category:*\n"
            for cat, amount in by_category.items():
                message += f"• {cat}: ${amount:.2f}\n"
        else:
            message += "No expenses recorded yet."

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        await update.message.reply_text(
            "⚠️ Sorry, I encountered an error fetching your stats."
        )


async def advice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /advice command — get AI financial tips."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/advice")
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
            "⚠️ Sorry, I encountered an error generating advice."
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

    # Check if user is in chat mode
    if user_id in chat_mode_users:
        await handle_chat_message(update, user_text)
    else:
        await handle_expense_message(update, user_text)


async def handle_chat_message(update: Update, user_text: str):
    """Handle message in chat mode — send to /chat endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/chat",
                json={"message": user_text},
            )
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
                f"{BACKEND_URL}/parse-expenses",
                json={"text": user_text},
            )
            data = response.json()

        saved_expenses = data.get("saved", [])

        if not saved_expenses:
            await update.message.reply_text(
                "❌ No expenses found in your message. Try something like:\n"
                "_I bought coffee for 5 and pizza for 10_",
                parse_mode="Markdown",
            )
            return

        # Build confirmation message
        message = "✅ *Saved:*\n\n"
        for exp in saved_expenses:
            message += f"• {exp['item']}: {exp['amount']} ({exp['category']})\n"

        await update.message.reply_text(message, parse_mode="Markdown")

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

    app = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("advice", advice))
    app.add_handler(CommandHandler("chat", chat_mode))
    app.add_handler(CommandHandler("exit", exit_chat_mode))

    # Register message handler (non-command text)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
