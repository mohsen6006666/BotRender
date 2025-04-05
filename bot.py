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
LOG_CHANNEL_ID = -1002699774923  # Replace with your channel ID

YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"

MOVIE_CACHE = {}
TORRENT_CACHE = {}
LOGGED_USERS = set()  # Tracks which users have been logged

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    username = update.effective_user.username

    # Only log once per user
    if user_id not in LOGGED_USERS:
        LOGGED_USERS.add(user_id)
        log_text = f"👤 {name}\n ├ id: {user_id}\n ├ username: @{username if username else 'N/A'}"
        try:
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_text)
        except Exception as e:
            logging.warning(f"Couldn't log user: {e}")

    welcome_msg = (
        "🎬 *Welcome to Torrent Finder Bot!*\n\n"
        "Send me the name of any movie, and I'll fetch available *torrent links* for you.\n"
        "Click on a *quality option* to download the *.torrent* file.\n\n"
        "_Tip: Use Webtor.io or any torrent downloader like aTorrent._"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    response = requests.get(YTS_API.format(query))

    if response.status_code != 200:
        await update.message.reply_text("API error. Try again later.")
        return

    data = response.json()
    movies = data.get("data", {}).get("movies", [])

    if not movies:
        await update.message.reply_text("No results found.")
        return

    keyboard = []
    added_titles = set()

    for movie in movies:
        title = movie["title_long"]
        if title in added_titles:
            continue
        added_titles.add(title)

        movie_id = str(movie["id"])
        MOVIE_CACHE[movie_id] = movie.get("torrents", [])
        keyboard.append([InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a movie:", reply_markup=reply_markup)

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
            quality = torrent.get("quality")
            callback_key = f"torrent_{movie_id}_{i}"
            TORRENT_CACHE[callback_key] = torrent.get("url")
            buttons.append([InlineKeyboardButton(quality, callback_data=callback_key)])

        await query.edit_message_text("Select a quality:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("torrent_"):
        torrent_url = TORRENT_CACHE.get(data)

        if not torrent_url:
            await query.edit_message_text("Torrent expired or not found.")
            return

        try:
            res = requests.get(torrent_url)
            if res.status_code != 200 or not res.content:
                await query.edit_message_text("Failed to download the file.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(res.content)
                tf_path = tf.name

            with open(tf_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="movie.torrent",
                    caption="Use [Webtor.io](https://webtor.io) or a torrent app to play it.",
                    parse_mode="Markdown",
                )

            await query.edit_message_text("Here’s your torrent file:")
        except Exception as e:
            logging.error(f"Error sending torrent: {e}")
            await query.edit_message_text("Error sending the file.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
