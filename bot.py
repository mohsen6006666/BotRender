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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = -1002699774923  # Your channel ID here
logged_users = set()

YTS_API = "https://yts.mx/api/v2/list_movies.json"
MOVIE_DETAILS_API = "https://yts.mx/api/v2/movie_details.json"

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in logged_users:
        logged_users.add(user.id)
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"New user: {user.mention_html()} (ID: {user.id})",
            parse_mode="HTML"
        )

    await update.message.reply_text(
        "**🎬 Welcome to Movie Torrent Bot!**\n\n"
        "Just type any movie name and I’ll fetch torrent files for you.\n\n"
        "▶️ Play online using [Webtor.io](https://webtor.io)\n"
        "⬇️ Download using **aTorrent** or **Flud** app\n\n"
        "_Example: Interstellar, Fight Club, John Wick_",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# Handle movie search
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    response = requests.get(YTS_API, params={"query_term": query})
    data = response.json()

    movies = data.get("data", {}).get("movies", [])
    if not movies:
        await update.message.reply_text("❌ No movies found. Try another name.")
        return

    buttons = [
        [InlineKeyboardButton(f"{m['title']} ({m['year']})", callback_data=f"movie_{m['id']}")]
        for m in movies[:5]
    ]

    await update.message.reply_text("🎥 Select a movie:", reply_markup=InlineKeyboardMarkup(buttons))

# Handle button actions
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        response = requests.get(MOVIE_DETAILS_API, params={"movie_id": movie_id, "with_torrents": "true"})
        movie = response.json().get("data", {}).get("movie", {})
        torrents = movie.get("torrents", [])

        if not torrents:
            await query.edit_message_text("❌ Torrent not available.")
            return

        quality_buttons = []
        for t in torrents:
            q = t.get("quality")
            s = t.get("size")
            url = t.get("url")
            quality_buttons.append(
                [InlineKeyboardButton(f"{q} - {s}", callback_data=f"torrent_{url}")]
            )

        await query.edit_message_text("✅ Choose your quality:", reply_markup=InlineKeyboardMarkup(quality_buttons))

    elif data.startswith("torrent_"):
        torrent_url = data.replace("torrent_", "")
        try:
            r = requests.get(torrent_url)
            r.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as f:
                f.write(r.content)
                f.flush()

                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(f.name, "rb"),
                    filename="movie.torrent",
                    caption="✅ Torrent fetched!\nPlay on [Webtor.io](https://webtor.io) or use aTorrent / Flud to download.",
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )

        except Exception as e:
            logger.error(f"Error sending torrent: {e}")
            await query.edit_message_text("❌ Error sending the file.")

# Main runner
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
