import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Store torrent links temporarily
torrent_map = {}

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎬 **Welcome to Movie Torrent Bot!** 🎬\n\n"
        "Just type the name of any movie.\n"
        "We’ll send you `.torrent` files directly.\n\n"
        "To watch/download: Upload the file to [Webtor.io](https://webtor.io) or use a torrent downloader."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Movie search handler
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    res = requests.get("https://yts.mx/api/v2/list_movies.json", params={"query_term": query})
    data = res.json()

    if not data["data"]["movie_count"]:
        await update.message.reply_text("❌ No results found.")
        return

    movies = data["data"]["movies"]
    buttons = [
        [InlineKeyboardButton(f"{m['title']} ({m['year']})", callback_data=f"movie_{m['id']}")]
        for m in movies
    ]
    await update.message.reply_text("🎥 *Select a movie:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

# Handle movie selection
async def movie_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = query.data.split("_")[1]

    res = requests.get("https://yts.mx/api/v2/movie_details.json", params={
        "movie_id": movie_id,
        "with_images": True,
        "with_cast": True
    })
    movie = res.json()["data"]["movie"]

    buttons = []
    for t in movie["torrents"]:
        label = f"{t['quality']} - {t['size']}"
        code = f"torrent_{t['url']}"
        torrent_map[code] = t["url"]
        buttons.append([InlineKeyboardButton(label, callback_data=code)])

    await query.message.reply_text(
        f"🎬 *{movie['title']} ({movie['year']})*\n\nChoose a quality:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

# Handle torrent selection
async def send_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    code = query.data
    url = torrent_map.get(code)
    if not url:
        await query.message.reply_text("❌ Torrent not found.")
        return

    filename = url.split("/")[-1]
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)

    await query.message.reply_document(open(filename, "rb"))
    os.remove(filename)

# Start the bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(movie_selected, pattern="^movie_"))
    app.add_handler(CallbackQueryHandler(send_torrent, pattern="^torrent_"))
    app.run_polling()

if __name__ == "__main__":
    main()
