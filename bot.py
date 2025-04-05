import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from user_logger import log_user

# Load .env if running locally
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

YTS_API_SEARCH = "https://yts.mx/api/v2/list_movies.json?query_term={}"
YTS_API_DETAILS = "https://yts.mx/api/v2/movie_details.json?movie_id={}&with_torrents=true"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await log_user(update, context)

    await update.message.reply_text(
        "**🎬 Welcome to Movie Magnet Bot!**\n\n"
        "Search any movie name and get the magnet link instantly.\n\n"
        "*Copy the link and paste it on* **[webtor.io](https://webtor.io)** *or open it using* "
        "[aTorrent](https://play.google.com/store/apps/details?id=com.utorrent.client).",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    url = YTS_API_SEARCH.format(query)

    try:
        res = requests.get(url).json()
        movies = res.get("data", {}).get("movies", [])

        if not movies:
            await update.message.reply_text("❌ No movies found.")
            return

        buttons = [
            [InlineKeyboardButton(f"{movie['title']} ({movie['year']})", callback_data=f"movie_{movie['id']}")]
            for movie in movies[:10]
        ]

        await update.message.reply_text("🎥 Select a movie:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("⚠️ Error searching for the movie.")


async def movie_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    movie_id = query.data.split("_")[1]
    url = YTS_API_DETAILS.format(movie_id)

    try:
        res = requests.get(url).json()
        movie = res["data"]["movie"]
        torrents = movie.get("torrents", [])
        title = movie.get("title")

        if not torrents:
            await query.edit_message_text("❌ No torrents available for this movie.")
            return

        buttons = [
            [InlineKeyboardButton(t["quality"], callback_data=f"magnet_{t['hash']}_{title.replace(' ', '_')}")]
            for t in torrents
        ]

        await query.edit_message_text(
            f"🎯 Choose quality for *{title}*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Details error: {e}")
        await query.edit_message_text("⚠️ Error getting movie info.")


async def magnet_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, hash_value, movie_name = query.data.split("_", 2)
    magnet_link = f"magnet:?xt=urn:btih:{hash_value}&dn={movie_name}"

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"**✅ Magnet Link Generated**\n\n"
                f"`{magnet_link}`\n\n"
                "*Copy the above link and paste it on* **[webtor.io](https://webtor.io)** "
                "*or open it with* [aTorrent](https://play.google.com/store/apps/details?id=com.utorrent.client)",
            ),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Magnet send error: {e}")
        await query.edit_message_text("⚠️ Error sending magnet link.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(movie_selected, pattern="^movie_"))
    app.add_handler(CallbackQueryHandler(magnet_selected, pattern="^magnet_"))

    logger.info("Bot is running.")
    app.run_polling()


if __name__ == "__main__":
    main()
