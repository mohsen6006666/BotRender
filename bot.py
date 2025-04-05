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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = -1001234567890  # replace with your log channel ID
logged_users = set()

YTS_API = "https://yts.mx/api/v2/list_movies.json"
MOVIE_DETAILS = "https://yts.mx/api/v2/movie_details.json?with_torrents=true"

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in logged_users:
        logged_users.add(user_id)
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"New user: {update.effective_user.mention_html()}",
            parse_mode="HTML"
        )

    await update.message.reply_text(
        "**Send me any movie name and I'll find torrent files for you.**\n\n"
        "- Play it on [Webtor.io](https://webtor.io)\n"
        "- Or use **aTorrent** / Flud to download\n\n"
        "_Just type the movie name and I'll handle the rest._",
        parse_mode="Markdown"
    )

# Search for movies
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    response = requests.get(YTS_API, params={"query_term": query})
    data = response.json()

    movies = data.get("data", {}).get("movies", [])
    if not movies:
        await update.message.reply_text("No movies found.")
        return

    buttons = [
        [InlineKeyboardButton(f"{m['title']} ({m['year']})", callback_data=f"movie_{m['id']}")]
        for m in movies[:5]
    ]

    await update.message.reply_text("🎥 Select a movie:", reply_markup=InlineKeyboardMarkup(buttons))

# Handle movie selection
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        response = requests.get(MOVIE_DETAILS, params={"movie_id": movie_id})
        movie = response.json().get("data", {}).get("movie", {})

        torrents = movie.get("torrents", [])
        if not torrents:
            await query.edit_message_text("No torrents available.")
            return

        buttons = []
        for t in torrents:
            quality = t["quality"]
            size = t["size"]
            buttons.append([
                InlineKeyboardButton(f"{quality} - {size}", callback_data=f"torrent_{t['url']}")
            ])

        await query.edit_message_text("Select quality:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("torrent_"):
        torrent_url = data.replace("torrent_", "")
        try:
            torrent_file = requests.get(torrent_url)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(torrent_file.content)
                tf.flush()
                tf.seek(0)

                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(tf.name, "rb"),
                    filename="movie.torrent",
                    caption="Use [Webtor](https://webtor.io) to stream or download using **aTorrent** or **Flud**.",
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Error sending torrent: {e}")
            await query.edit_message_text("Error sending the file.")
