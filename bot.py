import os
import logging
import requests
import tempfile
import uuid
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

MOVIE_CACHE = {}
TORRENT_CACHE = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Send a movie name to get torrent links.\n\n"
        "You’ll first choose a movie, then pick a quality (720p / 1080p etc).\n"
        "**Tip:** Use [Webtor](https://webtor.io) or any torrent app to play/download.",
        parse_mode="Markdown"
    )

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
    for movie in movies[:6]:  # show max 6 results
        key = str(uuid.uuid4())[:8]
        MOVIE_CACHE[key] = {
            "title": movie["title_long"],
            "torrents": movie["torrents"]
        }
        keyboard.append([InlineKeyboardButton(movie["title_long"], callback_data=f"movie|{key}")])

    await update.message.reply_text(
        "Select a movie:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie|"):
        key = data.split("|")[1]
        movie = MOVIE_CACHE.get(key)

        if not movie:
            await query.edit_message_text("Movie expired. Search again.")
            return

        keyboard = []
        for torrent in movie["torrents"]:
            tid = str(uuid.uuid4())[:8]
            TORRENT_CACHE[tid] = {
                "url": torrent["url"],
                "title": movie["title"],
                "quality": torrent["quality"]
            }
            keyboard.append([InlineKeyboardButton(torrent["quality"], callback_data=f"torrent|{tid}")])

        await query.edit_message_text(
            f"**{movie['title']}**\nChoose quality:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("torrent|"):
        tid = data.split("|")[1]
        info = TORRENT_CACHE.get(tid)

        if not info:
            await query.edit_message_text("Link expired. Search again.")
            return

        try:
            res = requests.get(info["url"])
            if res.status_code != 200:
                await query.edit_message_text("Failed to fetch torrent.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(res.content)
                tf.flush()
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(tf.name, 'rb'),
                    filename=f"{info['title']} [{info['quality']}].torrent",
                    caption="Play it on [Webtor](https://webtor.io) or use a torrent app.",
                    parse_mode="Markdown"
                )
            await query.edit_message_text("Here’s your torrent:")
        except Exception as e:
            logging.error(f"Torrent error: {e}")
            await query.edit_message_text("Error sending torrent.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
