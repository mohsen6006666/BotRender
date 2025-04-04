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

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOVIE_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"

# Cache for storing movie data
MOVIE_CACHE = {}
TORRENT_CACHE = {}

# Set up logging
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    welcome_msg = (
        "🎬 **Welcome to Torrent Finder Bot!** 🎬\n\n"
        "Send me the name of any movie, and I'll fetch available **torrent links** for you.\n"
        "Click on a **quality option** to download the **.torrent** file.\n\n"
        "**Tip:** Play it on Webtor or use any torrent downloader like **aTorrent**."
    )
    await update.message.reply_text(welcome_msg, disable_web_page_preview=True)

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for movies based on user query."""
    query = update.message.text.strip()
    response = requests.get(MOVIE_API.format(query))
    
    if response.status_code != 200:
        await update.message.reply_text("⚠️ API Error. Try again later.")
        return
    
    data = response.json()
    movies = data.get("data", {}).get("movies", [])
    
    if not movies:
        await update.message.reply_text("❌ No results found. Try another movie.")
        return

    keyboard = []
    for movie in movies:
        movie_id = str(movie["id"])
        MOVIE_CACHE[movie_id] = movie["torrents"]
        title = movie["title_long"]
        keyboard.append([InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 **Select a movie:**", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        torrents = MOVIE_CACHE.get(movie_id, [])

        buttons = []
        for i, torrent in enumerate(torrents):
            quality = torrent["quality"]
            torrent_url = torrent["url"]
            callback_key = f"torrent_{movie_id}_{i}"
            TORRENT_CACHE[callback_key] = torrent_url
            buttons.append([InlineKeyboardButton(quality, callback_data=callback_key)])

        await query.edit_message_text("🎥 **Choose quality:**", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("torrent_"):
        parts = data.split("_")
        movie_id = parts[1]
        index = int(parts[2])
        torrent_url = TORRENT_CACHE.get(data)

        if not torrent_url:
            await query.edit_message_text("⚠️ Torrent expired or not found.")
            return

        try:
            res = requests.get(torrent_url)
            if res.status_code != 200:
                await query.edit_message_text("❌ Failed to download torrent file.")
                return

            filename = f"{movie_id}_{index}.torrent"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(res.content)
                tf.flush()
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(tf.name, 'rb'),
                    filename=filename
                )
            await query.edit_message_text("✅ Here’s your torrent file.\n🎬 **Play it on Webtor or use any torrent downloader like aTorrent.**")
        except Exception as e:
            logging.error(f"Error sending torrent: {e}")
            await query.edit_message_text("❌ Error sending torrent file.")

def main():
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
