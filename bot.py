import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get your bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# A dictionary to store short torrent IDs
torrent_map = {}

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎬 *Welcome to Movie Torrent Bot!*\n\n"
        "Just type any movie name.\n"
        "We'll show you options and send you the .torrent file directly.\n\n"
        "Watch/download via [webtor.io](https://webtor.io) or use any torrent downloader."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Handle movie name search
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    res = requests.get("https://yts.mx/api/v2/list_movies.json", params={"query_term": query})
    data = res.json()

    if not data["data"]["movie_count"]:
        await update.message.reply_text("❌ No movies found.")
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
        "with_images": False,
        "with_cast": False
    })
    movie = res.json()["data"]["movie"]

    buttons = []
    for t in movie["torrents"]:
        label = f"{t['quality']} - {t['size']}"
        short_id = str(len(torrent_map))
        torrent_map[short_id] = t["url"]
        buttons.append([InlineKeyboardButton(label, callback_data=f"torrent_{short_id}")])

    await query.message.reply_text(
        f"🎬 *{movie['title']} ({movie['year']})*\n\nChoose a quality:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

# Handle torrent button click
async def send_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    short_id = query.data.split("_")[1]
    url = torrent_map.get(short_id)

    if not url:
        await query.message.reply_text("❌ Torrent not found.")
        return

    filename = url.split("/")[-1]
    response = requests.get(url)
    with open(filename, "wb") as f:
        f.write(response.content)

    await query.message.reply_document(document=open(filename, "rb"), filename=filename)
    os.remove(filename)

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(movie_selected, pattern="^movie_"))
    app.add_handler(CallbackQueryHandler(send_torrent, pattern="^torrent_"))
    app.run_polling()

if __name__ == "__main__":
    main()
