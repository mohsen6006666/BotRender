import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1002699774923  # Your private channel ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Send a test message to user
    await update.message.reply_text("Bot is working! Sending log to channel...")

    # Send a test message to your private channel
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"New user: {update.effective_user.first_name} (@{update.effective_user.username}) used /start"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
