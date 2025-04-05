import os
import logging
import requests
import tempfile

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache to store torrent data
torrent_cache = {}

# Start / Welcome message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Welcome to Movie Magnet Bot!\n\n"
        "Search any movie name and get the `.torrent` file instantly.\n\n"
        "To stream or download the movie, upload the `.torrent` file to *webtor.io* or use *aTorrent*.\n\n"
        "_Note: No link previews are shown here._",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# Handle movie search queries
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    url = f"https://yts.mx/api/v2/list_movies.json?query_term={query}"

    try:
        response = requests.get(url).json()
        movies = response.get("data", {}).get("movies", [])

        if not movies:
            await update.message.reply_text("❌ No movies found.")
            return

        keyboard = []
        for movie in movies[:10]:
            title = movie["title_long"]
            movie_id = movie["id"]
            torrent_cache[movie_id] = movie["torrents"]
            keyboard.append([
                InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")
            ])

        await update.message.reply_text(
            "🎥 Choose a movie:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("⚠️ Error while searching.")

# Handle movie selection
async def handle_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = int(query.data.split("_")[1])

    torrents = torrent_cache.get(movie_id, [])
    if not torrents:
        await query.edit_message_text("❌ Torrent info not found. Try again.")
        return

    buttons = []
    for torrent in torrents:
        quality = torrent["quality"]
        hash_val = torrent["hash"]
        buttons.append([
            InlineKeyboardButton(quality, callback_data=f"quality_{hash_val}")
        ])

    await query.edit_message_text(
        "🎯 Choose quality:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Handle quality selection
async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    hash_val = query.data.split("_")[1]
    torrent_url = f"https://yts.mx/torrent/download/{hash_val}"

    try:
        res = requests.get(torrent_url)
        if res.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tmp:
                tmp.write(res.content)
                tmp.flush()

                await context.bot.send_document(
                    chat_id=query.message.chat.id,
                    document=open(tmp.name, "rb"),
                    filename=f"{hash_val}.torrent",
                    caption="Use with *webtor.io* or *aTorrent* app.",
                    parse_mode="Markdown"
                )
        else:
            await query.edit_message_text("❌ Torrent download failed or not found.")
    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text("⚠️ Couldn't fetch the torrent.")

# Main entry
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(handle_movie, pattern="^movie_"))
    app.add_handler(CallbackQueryHandler(handle_quality, pattern="^quality_"))

    logger.info("Bot is up.")
    app.run_polling()

if __name__ == "__main__":
    main()
