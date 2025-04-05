from telegram import User
from telegram.ext import Application

# Replace this with your channel ID
LOG_CHANNEL_ID = -1002699774923

# Log function
async def log_user_start(user: User):
    msg = f"**New User Started Bot**\n\nName: {user.full_name}\nUsername: @{user.username}\nUser ID: `{user.id}`"
    
    # Import app instance safely (if needed)
    from bot import BOT_TOKEN
    app = Application.builder().token(BOT_TOKEN).build()
    await app.bot.send_message(chat_id=LOG_CHANNEL_ID, text=msg, parse_mode='Markdown')
