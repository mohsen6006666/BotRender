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

MOVIE_CACHE = {}
TORRENT_CACHE = {}

logging.basicConfig(level=logging.INFO)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🎬 **Welcome to Torrent Downloader Bot!** 🎬\n\n"
        "Just send me the name of a movie, and I'll fetch its **torrent links**.\n"
        "Click on a **quality option** to download the **.torrent** file.\n\n"
        "**Tip:** Play it on Webtor or download it using any torrent downloader."
    )
    await update.message.reply_text(welcome_msg, disable_web_page_preview=True)

# Search Movie Function
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    url = f"https://api.example.com/search?query={query}"  # Replace with your own torrent API

    response = requests.get(url)
    
    if response.status_code != 200:
        await update.message.reply_text("Error fetching torrent info.")
        return
    
    data = response.json()
    torrents = data.get("torrents", [])

    if not torrents:
        await update.message.reply_text("No results found.")
        return

    keyboard = []
    for torrent in torrents:
        title = torrent["title"]
        quality = torrent["quality"]
        torrent_url = torrent["url"]
        movie_id = str(torrent["id"])
        TORRENT_CACHE[movie_id] = torrent_url
        keyboard.append([InlineKeyboardButton(f"{title} ({quality})", callback_data=movie_id)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a movie:", reply_markup=reply_markup)

# Button Handler to send the torrent file
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = query.data

    torrent_url = TORRENT_CACHE.get(movie_id)

    if not torrent_url:
        await query.edit_message_text("Torrent expired or not found.")
        return

    try:
        res = requests.get(torrent_url)
        if res.status_code != 200:
            await query.edit_message_text("Failed to download the file.")
            return

        filename = f"{movie_id}.torrent"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
            tf.write(res.content)
            tf.flush()
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(tf.name, 'rb'),
                filename=filename
            )
        await query.edit_message_text("Here’s your torrent file:\n\nPlay it on Webtor or download it with a torrent downloader.")
    except Exception as e:
        logging.error(f"Error sending torrent: {e}")
        await query.edit_message_text("Error sending torrent file.")

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
