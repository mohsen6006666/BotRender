import os
import logging
import requests
import tempfile
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Load .env variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**🎬 Welcome to Movie Magnet Bot!**\n\n"
        "Search any movie name and get the `.torrent` file instantly.\n\n"
        "To stream or download the movie, upload the `.torrent` file to [webtor.io](https://webtor.io)",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# Search handler
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    url = f"https://yts.mx/api/v2/list_movies.json?query_term={query}"

    try:
        res = requests.get(url).json()
        movies = res.get("data", {}).get("movies", [])

        if not movies:
            await update.message.reply_text("❌ No results found.")
            return

        buttons = []
        for movie in movies[:10]:
            title = movie["title"]
            year = movie["year"]
            movie_id = movie["id"]
            buttons.append([InlineKeyboardButton(f"{title} ({year})", callback_data=f"movie_{movie_id}")])

        await update.message.reply_text("🎥 Select a movie:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("⚠️ Something went wrong while searching.")

# Movie selection
async def movie_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = query.data.split("_")[1]

    url = f"https://yts.mx/api/v2/movie_details.json?movie_id={movie_id}&with_torrents=true"
    try:
        res = requests.get(url).json()
        movie = res["data"]["movie"]
        title = movie["title"]
        torrents = movie["torrents"]

        buttons = []
        for t in torrents:
            quality = t["quality"]
            hash_val = t["hash"]
            buttons.append([InlineKeyboardButton(quality, callback_data=f"quality_{hash_val}_{title.replace(' ', '_')}")])

        if not buttons:
            await query.edit_message_text("❌ No torrents found for this movie.")
            return

        await query.edit_message_text(f"🎯 Choose quality for *{title}*:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Movie fetch error: {e}")
        await query.edit_message_text("⚠️ Failed to load torrents.")

# Quality selected
async def quality_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, hash_val, name = query.data.split("_", 2)

    torrent_url = f"https://yts.mx/torrent/download/{hash_val}"

    try:
        response = requests.get(torrent_url)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(response.content)
                tf.flush()
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=open(tf.name, "rb"),
                    filename=f"{name}.torrent",
                    caption="Use [webtor.io](https://webtor.io) or any torrent client to stream/download.",
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
        else:
            await query.edit_message_text("❌ Torrent not found.")
    except Exception as e:
        logger.error(f"Torrent error: {e}")
        await query.edit_message_text("⚠️ Could not send the torrent file.")

# Main
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
