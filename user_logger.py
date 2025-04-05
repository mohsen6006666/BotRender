# user_logger.py

logged_users = set()

def log_user(update, context):
    user = update.effective_user
    user_id = user.id
    name = user.full_name
    log_channel_id = -1002699774923  # your channel ID

    if user_id not in logged_users:
        logged_users.add(user_id)

        context.bot.send_message(
            chat_id=log_channel_id,
            text=f"New user: {name} (ID: {user_id})"
        )
