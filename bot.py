import os
import logging
import requests
import tempfile
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from user_logger import log_user  # Import from user_logger.py

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = -1002699774923  # Ensure your bot is admin in this channel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await log_user(update, context)  # Await log_user here

    await update.message.reply_text(
        "**🎬 Welcome to Movie Magnet Bot!**\n\n"
        "Search any movie name and get the `.torrent` file instantly.\n\n"
        "*Tip:* Upload the `.torrent` file to [webtor.io](https://webtor.io) or use [aTorrent](https://play.google.com/store/apps/details?id=com.utorrent.client) to stream/download.",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    url = f"https://yts.mx/api/v2/list_movies.json?query_term={query}"

    try:
        response = requests.get(url).json()
        movies = response.get("data", {}).get("movies", [])

        if not movies:
            await update.message.reply_text("❌ No movies found.")
            return

        buttons = []
        for movie in movies[:10]:
            title = movie["title"]
            year = movie["year"]
            movie_id = movie["id"]
            buttons.append([InlineKeyboardButton(f"{title} ({year})", callback_data=f"movie_{movie_id}")])

        await update.message.reply_text("🎥 Select a movie:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Error searching movie: {e}")
        await update.message.reply_text("⚠️ Failed to search movie.")

async def movie_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = query.data.split("_")[1]

    url = f"https://yts.mx/api/v2/movie_details.json?movie_id={movie_id}&with_torrents=true"
    try:
        response = requests.get(url).json()
        movie = response["data"]["movie"]
        title = movie["title"]
        torrents = movie.get("torrents", [])

        buttons = []
        for t in torrents:
            quality = t["quality"]
            hash_value = t["hash"]
            buttons.append([InlineKeyboardButton(f"{quality}", callback_data=f"quality_{hash_value}_{title.replace(' ', '_')}")])

        if not buttons:
            await query.edit_message_text("❌ No torrents available.")
            return

        await query.edit_message_text(f"🎯 Choose quality for *{title}*:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Error selecting movie: {e}")
        await query.edit_message_text("⚠️ Error getting movie info.")

async def quality_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, hash_value, movie_name = query.data.split("_", 2)
    torrent_url = f"https://yts.mx/torrent/download/{hash_value}"

    try:
        response = requests.get(torrent_url)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(response.content)
                tf.flush()
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=open(tf.name, 'rb'),
                    filename=f"{movie_name}.torrent",
                    caption="Play it on [webtor.io](https://webtor.io) or open with a torrent app.",
                    parse_mode="Markdown"
                )
        else:
            await query.edit_message_text("❌ Torrent not found.")
    except Exception as e:
        logger.error(f"Error sending torrent: {e}")
        await query.edit_message_text("⚠️ Could not send the file.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(movie_selected, pattern="^movie_"))
    app.add_handler(CallbackQueryHandler(quality_selected, pattern="^quality_"))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
