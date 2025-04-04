import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")

# YTS API URL
YTS_API_URL = "https://yts.mx/api/v2/list_movies.json"

# Stores torrent links temporarily
user_torrent_selection = {}

async def start(update: Update, context):
    """Send welcome message."""
    welcome_text = (
        "🎬 **Welcome to Movie Torrent Bot!** 🎬\n\n"
        "🔍 Just type a movie name to search.\n"
        "⬇️ Select a movie from the list.\n"
        "🎞 Choose the preferred torrent file.\n"
        "📥 The `.torrent` file will be sent to you."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def search_movie(update: Update, context):
    """Search for movies on YTS."""
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

    # Fetch movie details
    movie_url = f"https://yts.mx/api/v2/movie_details.json?movie_id={movie_id}&with_torrents=true"
    response = requests.get(movie_url)
    data = response.json()

    if data["status"] != "ok" or "movie" not in data["data"]:
        await query.message.reply_text("❌ No torrents found for this movie.")
        return

    movie = data["data"]["movie"]
    torrents = sorted(movie["torrents"], key=lambda x: x["quality"], reverse=True)  # Sort by quality

    keyboard = []
    for torrent in torrents:
        quality = torrent["quality"]
        size = torrent["size"]
        torrent_url = torrent["url"]

        # Store torrent link for later use
        user_torrent_selection[torrent_url] = torrent_url

        keyboard.append([
            InlineKeyboardButton(f"{quality} - {size}", callback_data=torrent_url)
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        f"🎬 **{movie['title']} ({movie['year']})**\n\n📥 Choose a torrent file:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_torrent_file(update: Update, context):
    """Send the selected torrent file to the user."""
    query = update.callback_query
    torrent_url = query.data

    if torrent_url not in user_torrent_selection:
        await query.message.reply_text("❌ Torrent file not found.")
        return

    # Download the torrent file
    torrent_response = requests.get(torrent_url)
    file_name = torrent_url.split("/")[-1]

    with open(file_name, "wb") as file:
        file.write(torrent_response.content)

    # Send the .torrent file to the user
    await query.message.reply_document(document=open(file_name, "rb"))

    # Delete the file after sending
    os.remove(file_name)

def main():
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(show_torrents, pattern="^\d+$"))
    app.add_handler(CallbackQueryHandler(send_torrent_file, pattern="^https://"))

    app.run_polling()

if __name__ == "__main__":
    main()
