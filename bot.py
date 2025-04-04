import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import requests

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Get bot token from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Base URL for YTS API
YTS_API_URL = "https://yts.mx/api/v2/list_movies.json"

async def start(update: Update, context):
    """Send a welcome message when the bot starts."""
    welcome_text = (
        "🎬 **Welcome to Movie Torrent Bot!** 🎬\n\n"
        "🔍 Just type a movie name to search.\n"
        "⬇️ Select a movie from the list.\n"
        "🎞 Choose the preferred torrent file.\n"
        "📥 Download and watch via **[webtor.io](https://webtor.io)** or a torrent client."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def search_movie(update: Update, context):
    """Search for a movie on YTS and show results."""
    query = update.message.text.strip()
    response = requests.get(YTS_API_URL, params={"query_term": query})
    data = response.json()

    if data["status"] != "ok" or not data["data"]["movie_count"]:
        await update.message.reply_text("❌ No results found. Try another movie.")
        return

    movies = data["data"]["movies"]
    keyboard = [
        [InlineKeyboardButton(f"{movie['title']} ({movie['year']})", callback_data=str(movie['id']))]
        for movie in movies
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🎥 **Select a movie:**", reply_markup=reply_markup, parse_mode="Markdown")

async def show_torrents(update: Update, context):
    """Show available torrents for the selected movie."""
    query = update.callback_query
    movie_id = query.data

    response = requests.get(YTS_API_URL, params={"movie_id": movie_id})
    data = response.json()

    if data["status"] != "ok" or not data["data"]["movie_count"]:
        await query.message.reply_text("❌ No torrents found for this movie.")
        return

    movie = data["data"]["movies"][0]
    torrents = movie["torrents"]
    
    keyboard = [
        [InlineKeyboardButton(f"{torrent['quality']} - {torrent['size']}", url=torrent['url'])]
        for torrent in torrents
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        f"🎬 **{movie['title']} ({movie['year']})**\n\n📥 Choose a torrent:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def main():
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(show_torrents))

    app.run_polling()

if __name__ == "__main__":
    main()
