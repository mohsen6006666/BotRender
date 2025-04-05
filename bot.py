import os
import logging
import tempfile
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL_ID = -1002699774923  # Replace with your private channel ID
YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"

# Caches
MOVIE_CACHE = {}
TORRENT_CACHE = {}
LOGGED_USERS = set()  # Keeps track of users already logged

# Logging
logging.basicConfig(level=logging.INFO)

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    # Only send log once per user
    if user_id not in LOGGED_USERS:
        LOGGED_USERS.add(user_id)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=f"👤 New User Started: {user_name} (ID: {user_id})"
            )
        except Exception as e:
            logging.warning(f"Failed to log user: {e}")

    welcome_msg = (
        "🎬 *Welcome to Movie Search Bot!*\n\n"
        "Send me the name of any movie, and I’ll fetch available *torrent files* for you.\n"
        "Tap a movie, then pick a *quality* to download the `.torrent` file.\n\n"
        "_Use it with Webtor.io or any torrent app._"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

# Handle movie name search
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    response = requests.get(YTS_API.format(query))

    if response.status_code != 200:
        await update.message.reply_text("Error fetching from API. Try again later.")
        return

    data = response.json()
    movies = data.get("data", {}).get("movies", [])

    if not movies:
        await update.message.reply_text("No movies found.")
        return

    keyboard = []
    for movie in movies:
        movie_id = str(movie["id"])
        if movie_id in MOVIE_CACHE:
            continue  # avoid duplicates
        MOVIE_CACHE[movie_id] = movie["torrents"]
        title = movie["title_long"]
        keyboard.append([InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")])

    await update.message.reply_text("🎥 *Select a movie:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# Handle button presses
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        torrents = MOVIE_CACHE.get(movie_id, [])

        if not torrents:
            await query.edit_message_text("No torrents found for this movie.")
            return

        buttons = []
        for i, torrent in enumerate(torrents):
            quality = torrent["quality"]
            callback_key = f"torrent_{movie_id}_{i}"
            TORRENT_CACHE[callback_key] = torrent["url"]
            buttons.append([InlineKeyboardButton(quality, callback_data=callback_key)])

        await query.edit_message_text("🧲 *Choose quality:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    elif data.startswith("torrent_"):
        torrent_url = TORRENT_CACHE.get(data)

        if not torrent_url:
            await query.edit_message_text("Torrent expired or not found.")
            return

        try:
            res = requests.get(torrent_url)
            if res.status_code != 200:
                await query.edit_message_text("Failed to fetch torrent file.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(res.content)
                tf.flush()
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(tf.name, 'rb'),
                    filename="movie.torrent",
                    caption="Here's your torrent file. You can use it with Webtor.io or any torrent downloader.",
                )
            await query.edit_message_text("✅ Torrent file sent!")
        except Exception as e:
            logging.error(f"Error sending torrent: {e}")
            await query.edit_message_text("Error sending the file.")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
