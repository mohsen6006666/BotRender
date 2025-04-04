import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import uuid

BOT_TOKEN = os.getenv("BOT_TOKEN")
YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"

MOVIE_CACHE = {}  # Maps movie_id to torrent list
TORRENT_CACHE = {}  # Maps short ID to URL

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "Welcome to YTS Torrent Bot!\n\n"
        "Just send me the name of any movie.\n"
        "I'll find it on YTS and give you torrent download options.\n\n"
        "**Tip:** Upload the .torrent file to [webtor.io](https://webtor.io) to stream/download it easily!"
    )
    await update.message.reply_text(welcome_msg)

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    response = requests.get(YTS_API.format(query))
    data = response.json()

    movies = data.get("data", {}).get("movies", [])
    if not movies:
        await update.message.reply_text("No results found.")
        return

    keyboard = []
    for movie in movies:
        movie_id = str(movie["id"])
        MOVIE_CACHE[movie_id] = movie["torrents"]
        title = movie["title_long"]
        keyboard.append([InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")])

    await update.message.reply_text("Select a movie:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        torrents = MOVIE_CACHE.get(movie_id, [])

        buttons = []
        for torrent in torrents:
            quality = torrent["quality"]
            torrent_url = torrent["url"]
            unique_id = str(uuid.uuid4())[:8]
            TORRENT_CACHE[unique_id] = torrent_url
            buttons.append([InlineKeyboardButton(quality, callback_data=f"torrent_{unique_id}")])

        await query.edit_message_text("Choose quality:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("torrent_"):
        unique_id = data.split("_")[1]
        torrent_url = TORRENT_CACHE.get(unique_id)

        if not torrent_url:
            await query.edit_message_text("Torrent expired or not found.")
            return

        await query.edit_message_text("Here’s your torrent file:")
        await context.bot.send_document(chat_id=update.effective_chat.id, document=torrent_url)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
