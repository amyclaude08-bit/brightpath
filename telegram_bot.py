"""
BrightPath — Telegram Bot
Run: python telegram_bot.py
Requires: ANTHROPIC_API_KEY and TELEGRAM_BOT_TOKEN in environment
"""

import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from orchestrator import process_message_for_telegram, init_db

logging.basicConfig(level=logging.INFO)

ALLOWED_CHAT_IDS = [8712569350]  # Optional: add your Telegram chat ID here to restrict access

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 BrightPath Ops Assistant ready.\n\nSend me any inbound message to process it through the system."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Optional access control
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        await update.message.reply_text("⛔ Unauthorised.")
        return

    inbound = update.message.text
    await update.message.reply_text("⏳ Processing...")

    result = process_message_for_telegram(inbound)

    # Send the Telegram summary
    await update.message.reply_text(result["summary"])

    # Send action alert if needed
    if result.get("action"):
        await update.message.reply_text(f"⚠️ ACTION NEEDED: {result['action']}")

    if result.get("value"):
        await update.message.reply_text(f"💰 {result['value']}")

    if result.get("risk"):
        await update.message.reply_text(f"🚨 {result['risk']}")

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")

    init_db()
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()