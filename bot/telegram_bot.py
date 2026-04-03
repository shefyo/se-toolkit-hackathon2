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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome_message = (
        "👋 Welcome to *SmartReceipt*!\n\n"
        "I'm your AI-powered expense tracker.\n"
        "Just send me a message with your expenses, and I'll log them for you.\n\n"
        "*Example:*\n"
        "_I bought coffee for 5 and pizza for 10_"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages and send to backend for parsing."""
    user_text = update.message.text

    # Send to backend for parsing
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

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
