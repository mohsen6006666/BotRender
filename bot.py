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
LOG_CHANNEL_ID = -1002699774923  # Your private log channel ID
YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"

# Caching
MOVIE_CACHE = {}
TORRENT_CACHE = {}
LOGGED_USERS = set()

logging.basicConfig(level=logging.INFO)

# START command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in LOGGED_USERS:
        LOGGED_USERS.add(user_id)
        user_info = update.effective_user
        msg = (
            f"👤 User Started Bot\n"
            f"├ ID: `{user_info.id}`\n"
            f"├ Name: {user_info.first_name}\n"
            f"├ Username: @{user_info.username if user_info.username else 'N/A'}\n"
        )
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=msg, parse_mode="Markdown")

    welcome_msg = (
        "🎬 **Welcome to Torrent Finder Bot!**\n\n"
        "Send me the name of any movie and I’ll fetch available **torrent links**.\n"
        "Tap on the quality you want and I’ll send the `.torrent` file.\n\n"
        "_Use [Webtor.io](https://webtor.io) or any torrent app to play it._"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown", disable_web_page_preview=True)

# Movie search
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    response = requests.get(YTS_API.format(query))
    
    if response.status_code != 200:
        await update.message.reply_text("API error. Try again later.")
        return

    data = response.json()
    movies = data.get("data", {}).get("movies", [])
    keyboard = []

    for movie in movies:
        movie_id = str(movie["id"])
        torrents = movie.get("torrents", [])

        if not torrents:
            continue  # skip if no torrents

        MOVIE_CACHE[movie_id] = torrents
        title = movie["title_long"]
        keyboard.append([InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")])

    if not keyboard:
        await update.message.reply_text("No torrents found for this movie.")
        return

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose the movie you want:", reply_markup=reply_markup)

# Button press (movie selection & quality)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        torrents = MOVIE_CACHE.get(movie_id, [])

        if not torrents:
            await query.edit_message_text("No torrent options available.")
            return

        buttons = []
        for i, torrent in enumerate(torrents):
            quality = torrent.get("quality", "Unknown")
            callback_key = f"torrent_{movie_id}_{i}"
            TORRENT_CACHE[callback_key] = torrent["url"]
            buttons.append([InlineKeyboardButton(quality, callback_data=callback_key)])

        await query.edit_message_text("Select the quality you want:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("torrent_"):
        torrent_url = TORRENT_CACHE.get(data)
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
                    chat_id=query.message.chat_id,
                    document=open(tf.name, 'rb'),
                    filename="movie.torrent",
                    caption="Use Webtor.io or a torrent app to play it.",
                )
            await query.edit_message_text("Here’s your torrent file:")
        except Exception as e:
            logging.error(f"Error sending torrent: {e}")
            await query.edit_message_text("Error sending the file.")

# Main bot runner
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
