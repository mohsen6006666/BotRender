from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from user_logger import log_user_start

BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'  # Replace with your bot token

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"Hey {user.first_name}, welcome to MovieFlix!")
    
    # Log the user to your channel
    await log_user_start(user)

# Main bot setup
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
