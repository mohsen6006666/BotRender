# user_logger.py

from telegram import Update
from telegram.ext import ContextTypes

logged_users = set()
log_channel_id = -1002699774923  # Your private channel ID

async def log_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    name = user.full_name

    if user_id not in logged_users:
        logged_users.add(user_id)

        try:
            await context.bot.send_message(
                chat_id=log_channel_id,
                text=f"New user: {name} (ID: {user_id})"
            )
        except Exception as e:
            print(f"[Logger Error] Failed to send log: {e}")
