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

# Load bot token from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables!")

# YTS API URL
YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"

# Caching data
MOVIE_CACHE = {}
TORRENT_CACHE = {}

# Set up logging
logging.basicConfig(level=logging.INFO)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🎬 **Welcome to YTS Torrent Bot!** 🎬\n\n"
        "Just send me the name of a movie, and I'll fetch its **torrent links** from YTS.\n"
        "Click on a **quality option** to download the **.torrent** file.\n\n"
        "**Tip:** Upload the torrent file to [webtor.io](https://webtor.io) to stream instantly!"
    )
    await update.message.reply_text(welcome_msg, disable_web_page_preview=True)

# Search movie handler
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    response = requests.get(YTS_API.format(query))

    if response.status_code != 200:
        await update.message.reply_text("❌ YTS API error. Try again later.")
        return

    data = response.json()
    movies = data.get("data", {}).get("movies", [])

    if not movies:
        await update.message.reply_text("❌ No results found for your search.")
        return

    keyboard = []
    for movie in movies:
        movie_id = str(movie["id"])
        MOVIE_CACHE[movie_id] = movie["torrents"]  # Cache torrents
        title = movie["title_long"]
        keyboard.append([InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎥 **Select a movie:**", reply_markup=reply_markup)

# Handle button clicks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        torrents = MOVIE_CACHE.get(movie_id, [])

        if not torrents:
            await query.edit_message_text("❌ No torrents available.")
            return

        buttons = []
        for i, torrent in enumerate(torrents):
            quality = torrent["quality"]
            torrent_url = torrent["url"]
            callback_key = f"torrent_{movie_id}_{i}"
            TORRENT_CACHE[callback_key] = torrent_url
            buttons.append([InlineKeyboardButton(quality, callback_data=callback_key)])

        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("🎞 **Choose quality:**", reply_markup=reply_markup)

    elif data.startswith("torrent_"):
        parts = data.split("_")
        movie_id = parts[1]
        index = int(parts[2])
        torrent_url = TORRENT_CACHE.get(data)

        if not torrent_url:
            await query.edit_message_text("❌ Torrent expired or not found.")
            return

        try:
            res = requests.get(torrent_url)
            if res.status_code != 200:
                await query.edit_message_text("❌ Failed to download the file.")
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
            await query.edit_message_text("✅ Here’s your torrent file:")
        except Exception as e:
            logging.error(f"Error sending torrent: {e}")
            await query.edit_message_text("❌ Error sending torrent file.")

# Main function to start the bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Start polling
    app.run_polling()

# Run the bot
if __name__ == "__main__":
    main()
