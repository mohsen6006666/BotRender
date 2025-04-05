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

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = -1001234567890  # Replace with your private channel ID
logged_users = set()  # In-memory tracking

YTS_API = "https://yts.mx/api/v2/list_movies.json"
TORRENT_API = "https://yts.mx/api/v2/movie_details.json?with_torrents=true"

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in logged_users:
        logged_users.add(user_id)
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"New user started bot: {update.effective_user.mention_html()}", parse_mode="HTML")

    await update.message.reply_text("Send me a movie name to search torrents.")

# Handle movie name
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    response = requests.get(YTS_API, params={"query_term": query})
    data = response.json()

    if data.get("data", {}).get("movie_count", 0) == 0:
        await update.message.reply_text("No movies found.")
        return

    movies = data["data"]["movies"][:5]  # Max 5 options
    buttons = [
        [InlineKeyboardButton(movie["title"], callback_data=str(movie["id"]))]
        for movie in movies
    ]

    await update.message.reply_text("🎥 Select a movie:", reply_markup=InlineKeyboardMarkup(buttons))

# Handle movie selection
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    movie_id = query.data
    response = requests.get(TORRENT_API, params={"movie_id": movie_id})
    data = response.json()

    torrents = data.get("data", {}).get("movie", {}).get("torrents", [])

    if not torrents:
        await query.edit_message_text("Torrent expired or not found.")
        return

    for torrent in torrents:
        magnet_url = torrent["url"]
        try:
            torrent_file = requests.get(magnet_url)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(torrent_file.content)
                tf.flush()
                tf.seek(0)

                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(tf.name, "rb"),
                    filename="movie.torrent",
                    caption="Use [Webtor.io](https://webtor.io) to stream or any torrent client to download.",
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Error sending torrent: {e}")
            await query.edit_message_text("Error sending the file.")
        break  # send only one torrent

# Main
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
