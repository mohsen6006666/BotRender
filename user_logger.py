# user_logger.py

async def log_user(update, context):
    user = update.effective_user
    user_id = user.id
    name = user.full_name
    log_channel_id = -1002699774923  # Your channel ID

    try:
        await context.bot.send_message(
            chat_id=log_channel_id,
            text=f"New user started bot:\n\nName: {name}\nID: {user_id}"
        )
    except Exception as e:
        print(f"Error logging user: {e}")
