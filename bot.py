import os
import logging
import requests
import tempfile
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = -1002699774923  # Optional logging channel

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logged_users = set()

# Welcome /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    if user_id not in logged_users:
        logged_users.add(user_id)
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"New user started the bot:\n\nName: {name}\nID: {user_id}"
            )
        except Exception as e:
            logger.warning(f"User logging failed: {e}")

    await update.message.reply_text(
        "**🎬 Welcome to YTS Torrent Bot!**\n\n"
        "Type the name of any movie, and I'll send you available `.torrent` files.\n\n"
        "To stream or download: upload the file to [webtor.io](https://webtor.io) "
        "or use any torrent app.",
        parse_mode="Markdown"
    )

# Movie search handler
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
            buttons.append([
                InlineKeyboardButton(f"{title} ({year})", callback_data=f"movie_{movie_id}")
            ])

        await update.message.reply_text(
            "🎥 Select a movie:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("⚠️ Failed to search movies.")

# Movie selection callback
async def movie_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = query.data.split("_")[1]

    url = f"https://yts.mx/api/v2/movie_details.json?movie_id={movie_id}&with_torrents=true"
    try:
        response = requests.get(url).json()
        movie = response["data"]["movie"]
        torrents = movie["torrents"]
        title = movie["title"]

        buttons = []
        for t in torrents:
            quality = t["quality"]
            hash_value = t["hash"]
            buttons.append([
                InlineKeyboardButton(
                    f"{quality}",
                    callback_data=f"quality_{hash_value}_{title.replace(' ', '_')}"
                )
            ])

        await query.edit_message_text(
            f"🎯 Choose quality for *{title}*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"Movie select error: {e}")
        await query.edit_message_text("⚠️ Error loading torrent info.")

# Quality button callback
async def quality_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, hash_value, movie_name = query.data.split("_", 2)
    torrent_url = f"https://yts.mx/torrent/download/{hash_value}"

    try:
        torrent_response = requests.get(torrent_url, stream=True)
        if torrent_response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
                tf.write(torrent_response.content)
                tf.flush()
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=open(tf.name, 'rb'),
                    filename=f"{movie_name}.torrent",
                    caption="Stream via [webtor.io](https://webtor.io) or download with your torrent app.",
                    parse_mode="Markdown"
                )
            await query.edit_message_text("✅ Torrent file sent!")
        else:
            await query.edit_message_text("❌ Torrent link broken or expired.")
    except Exception as e:
        logger.error(f"Torrent send error: {e}")
        await query.edit_message_text("⚠️ Failed to send torrent file.")

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(movie_selected, pattern="^movie_"))
    app.add_handler(CallbackQueryHandler(quality_selected, pattern="^quality_"))

    logger.info("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
