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
LOG_CHANNEL_ID = -1002699774923
logged_users = set()

YTS_API = "https://yts.mx/api/v2/list_movies.json"
MOVIE_DETAILS_API = "https://yts.mx/api/v2/movie_details.json"

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in logged_users:
        logged_users.add(user.id)
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"New user: {user.mention_html()} (ID: {user.id})",
            parse_mode="HTML"
        )

    await update.message.reply_text(
        "**🎬 Welcome to Movie Torrent Bot!**\n\n"
        "Type any movie name to get torrent download.\n"
        "Example: *John Wick*, *Inception*, *Fight Club*\n\n"
        "▶️ Play online: [Webtor.io](https://webtor.io)\n"
        "⬇️ Use Flud / aTorrent to download.",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# Search handler
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    response = requests.get(YTS_API, params={"query_term": query})
    data = response.json()

    movies = data.get("data", {}).get("movies", [])
    if not movies:
        await update.message.reply_text("❌ No movies found. Try again.")
        return

    buttons = [
        [InlineKeyboardButton(f"{m['title']} ({m['year']})", callback_data=f"movie_{m['id']}")]
        for m in movies[:5]
    ]

    await update.message.reply_text("🎥 Select a movie:", reply_markup=InlineKeyboardMarkup(buttons))

# Button click handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        response = requests.get(MOVIE_DETAILS_API, params={"movie_id": movie_id, "with_images": True, "with_cast": True})
        movie = response.json().get("data", {}).get("movie", {})
        torrents = movie.get("torrents", [])

        if not torrents:
            await query.edit_message_text("❌ Torrent not available for this movie.")
            return

        quality_buttons = []
        for t in torrents:
            quality = t["quality"]
            size = t["size"]
            url = t["url"]
            quality_buttons.append([
                InlineKeyboardButton(f"{quality} - {size}", callback_data=f"torrent_{url}")
            ])

        await query.edit_message_text("🎯 Choose quality to get torrent:", reply_markup=InlineKeyboardMarkup(quality_buttons))

    elif data.startswith("torrent_"):
        torrent_url = data.replace("torrent_", "")
        try:
            r = requests.get(torrent_url)
            r.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(r.content)
                tf.flush()

                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(tf.name, "rb"),
                    filename="movie.torrent",
                    caption="✅ Torrent ready!\nUse Flud or aTorrent to download.\nYou can also try [Webtor.io](https://webtor.io) to stream.",
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )

        except Exception as e:
            logger.error(f"Error sending torrent: {e}")
            await query.edit_message_text("❌ Error sending the file.")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
