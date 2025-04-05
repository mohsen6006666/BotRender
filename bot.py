import os
import logging
import requests
import tempfile
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
        title = movie["title_long"]
        for i, torrent in enumerate(movie["torrents"]):
            callback_data = f"dl|{torrent['url']}|{title}|{torrent['quality']}"
            button_text = f"{title} - {torrent['quality']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a torrent quality:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("dl|"):
        try:
            _, url, title, quality = data.split("|", 3)
            res = requests.get(url)
            if res.status_code != 200:
                await query.edit_message_text("Failed to download torrent.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(res.content)
                tf.flush()
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(tf.name, 'rb'),
                    filename=f"{title} [{quality}].torrent",
                    caption="Play it on [Webtor](https://webtor.io) or use a torrent app.",
                    parse_mode="Markdown"
                )
            await query.edit_message_text("Here's your torrent file:")
        except Exception as e:
            logging.error(f"Download error: {e}")
            await query.edit_message_text("Error sending file.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
