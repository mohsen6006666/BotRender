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

BOT_TOKEN = os.getenv("BOT_TOKEN")
YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"
CHANNEL_ID = -1002699774923  # Replace with your private channel ID

MOVIE_CACHE = {}
TORRENT_CACHE = {}

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🎬 **Welcome to Torrent Finder Bot!** 🎬\n\n"
        "Send me the name of any movie, and I'll fetch available **torrent links** for you.\n"
        "Click on a **quality option** to download the **.torrent** file.\n\n"
        "**Tip:** Play it on [Webtor](https://webtor.io) or use any torrent downloader like **aTorrent**."
    )
    await update.message.reply_text(welcome_msg, disable_web_page_preview=True, parse_mode="Markdown")

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    response = requests.get(YTS_API.format(query))
    
    if response.status_code != 200:
        await update.message.reply_text("API error. Try again later.")
        return
    
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

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a movie:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        torrents = MOVIE_CACHE.get(movie_id, [])

        buttons = []
        for i, torrent in enumerate(torrents):
            quality = torrent["quality"]
            callback_key = f"torrent_{movie_id}_{i}"
            TORRENT_CACHE[callback_key] = (torrent["url"], quality)
            buttons.append([InlineKeyboardButton(quality, callback_data=callback_key)])

        await query.edit_message_text("Choose quality:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("torrent_"):
        torrent_url, quality = TORRENT_CACHE.get(data, (None, None))

        if not torrent_url:
            await query.edit_message_text("Torrent expired or not found.")
            return

        try:
            res = requests.get(torrent_url)
            if res.status_code != 200:
                await query.edit_message_text("Failed to download the file.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(res.content)
                tf.flush()
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(tf.name, 'rb'),
                    filename="movie.torrent",
                    caption="Play it on [Webtor](https://webtor.io) or download using **aTorrent**.",
                    parse_mode="Markdown"
                )

            await query.edit_message_text("Here’s your torrent file:")

            # Log to your private channel
            user = update.effective_user
            log_text = f"User [{user.first_name}](tg://user?id={user.id}) downloaded a **{quality}** torrent."
            await context.bot.send_message(chat_id=CHANNEL_ID, text=log_text, parse_mode="Markdown")

        except Exception as e:
            logging.error(f"Error sending torrent: {e}")
            await query.edit_message_text("Error sending the file.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
