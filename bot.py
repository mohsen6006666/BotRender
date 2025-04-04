import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"
TORRENT_CACHE = {}

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "Welcome to YTS Torrent Bot!\n\n"
        "Just send me the name of any movie.\n"
        "I'll find it on YTS and give you torrent download options.\n\n"
        "**Tip:** After downloading, upload the .torrent file to [webtor.io](https://webtor.io) "
        "to stream/download it easily!"
    )
    await update.message.reply_text(welcome_msg)

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    response = requests.get(YTS_API.format(query))
    data = response.json()

    if not data["data"]["movies"]:
        await update.message.reply_text("No results found.")
        return

    keyboard = []
    for movie in data["data"]["movies"]:
        movie_id = str(movie["id"])
        title = movie["title_long"]
        TORRENT_CACHE[movie_id] = movie["torrents"]
        keyboard.append([InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a movie:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        torrents = TORRENT_CACHE.get(movie_id)

        if not torrents:
            await query.edit_message_text("Torrent info expired. Please search again.")
            return

        buttons = []
        for torrent in torrents:
            quality = torrent["quality"]
            url = torrent["url"]
            buttons.append([InlineKeyboardButton(quality, callback_data=f"torrent_{url}")])

        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("Choose quality:", reply_markup=reply_markup)

    elif data.startswith("torrent_"):
        url = data.replace("torrent_", "")
        await query.edit_message_text("Here’s your torrent file:")
        await context.bot.send_document(chat_id=update.effective_chat.id, document=url)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
