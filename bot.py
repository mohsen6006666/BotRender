import os import logging import requests from flask import Flask, request from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

Enable logging

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

Get bot token and webhook URL

BOT_TOKEN = os.getenv("BOT_TOKEN") WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Set this in Render

A dictionary to store short torrent IDs

torrent_map = {}

Initialize Flask app

app = Flask(name)

@app.route('/') def home(): return "Bot is running!"

@app.route(f'/{BOT_TOKEN}', methods=['POST']) def webhook(): update = Update.de_json(request.get_json(), app.bot) app.bot.process_update(update) return "OK", 200

/start command handler

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): welcome_text = ( "🎬 Welcome to Movie Torrent Bot!\n\n" "Just type any movie name.\n" "We'll show you options and send you the .torrent file directly.\n\n" "Watch/download via webtor.io or use any torrent downloader." ) await update.message.reply_text(welcome_text, parse_mode="Markdown")

Handle movie name search

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.message.text.strip() res = requests.get("https://yts.mx/api/v2/list_movies.json", params={"query_term": query}) data = res.json()

if not data["data"]["movie_count"]:
    await update.message.reply_text("❌ No movies found.")
    return

movies = data["data"]["movies"]
buttons = [
    [InlineKeyboardButton(f"{m['title']} ({m['year']})", callback_data=f"movie_{m['id']}")]
    for m in movies
]
await update.message.reply_text("🎥 *Select a movie:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

Handle movie selection

async def movie_selected(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() movie_id = query.data.split("_")[1]

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

Handle torrent button click

async def send_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() short_id = query.data.split("_")[1] url = torrent_map.get(short_id)

if not url:
    await query.message.reply_text("❌ Torrent not found.")
    return

filename = url.split("/")[-1]
response = requests.get(url)
with open(filename, "wb") as f:
    f.write(response.content)

await query.message.reply_document(document=open(filename, "rb"), filename=filename)
os.remove(filename)

Main function

def main(): global app app.bot = Application.builder().token(BOT_TOKEN).build() app.bot.add_handler(CommandHandler("start", start)) app.bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie)) app.bot.add_handler(CallbackQueryHandler(movie_selected, pattern="^movie_")) app.bot.add_handler(CallbackQueryHandler(send_torrent, pattern="^torrent_"))

# Set webhook
app.bot.initialize()
app.bot.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# Start Flask server
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

if name == "main": main()

