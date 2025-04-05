import os import logging import tempfile import requests from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters )

BOT_TOKEN = os.getenv("BOT_TOKEN") LOG_CHANNEL_ID = -1002699774923  # Replace with your private channel ID YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term={}"

MOVIE_CACHE = {} TORRENT_CACHE = {} LOGGED_USERS = set()

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id if user_id not in LOGGED_USERS: LOGGED_USERS.add(user_id) text = f"New user started bot:\nID: {user_id}\nUsername: @{update.effective_user.username}" try: await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=text) except Exception as e: logging.warning(f"Failed to send log to channel: {e}")

welcome_msg = (
    "🎬 *Welcome to Torrent Finder Bot!*\n\n"
    "Send me any movie name. I’ll fetch torrent links with quality options.\n"
    "Click a quality to download the `.torrent` file.\n\n"
    "_Play on [Webtor](https://webtor.io) or use a torrent app like aTorrent._"
)
await update.message.reply_text(welcome_msg, parse_mode="Markdown", disable_web_page_preview=True)

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.message.text.strip() response = requests.get(YTS_API.format(query))

if response.status_code != 200:
    await update.message.reply_text("YTS API error. Try again later.")
    return

data = response.json()
movies = data.get("data", {}).get("movies", [])

if not movies:
    await update.message.reply_text("No results found for that movie.")
    return

keyboard = []
for movie in movies:
    movie_id = str(movie["id"])
    if movie_id not in MOVIE_CACHE:
        MOVIE_CACHE[movie_id] = movie.get("torrents", [])
        title = movie.get("title_long", "Movie")
        keyboard.append([InlineKeyboardButton(title, callback_data=f"movie_{movie_id}")])

reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text("Select a movie:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() data = query.data

if data.startswith("movie_"):
    movie_id = data.split("_")[1]
    torrents = MOVIE_CACHE.get(movie_id, [])

    if not torrents:
        await query.edit_message_text("No torrents found for this movie.")
        return

    buttons = []
    for i, torrent in enumerate(torrents):
        quality = torrent.get("quality", "Unknown")
        callback_key = f"torrent_{movie_id}_{i}"
        TORRENT_CACHE[callback_key] = torrent.get("url")
        buttons.append([InlineKeyboardButton(quality, callback_data=callback_key)])

    await query.edit_message_text("Choose a quality:", reply_markup=InlineKeyboardMarkup(buttons))

elif data.startswith("torrent_"):
    torrent_url = TORRENT_CACHE.get(data)

    if not torrent_url:
        await query.edit_message_text("Torrent not available.")
        return

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(torrent_url, headers=headers, timeout=10)
        if res.status_code != 200:
            raise Exception("File not reachable.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".torrent") as tf:
            tf.write(res.content)
            tf.flush()
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=open(tf.name, "rb"),
                filename="movie.torrent",
                caption="Play it on [Webtor](https://webtor.io) or open in aTorrent.",
                parse_mode="Markdown"
            )
        await query.edit_message_text("Here is your torrent file:")
    except Exception as e:
        logging.error(f"Torrent send failed: {e}")
        await query.edit_message_text("Error sending the file.")

def main(): app = Application.builder().token(BOT_TOKEN).build() app.add_handler(CommandHandler("start", start)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie)) app.add_handler(CallbackQueryHandler(button_handler)) app.run_polling()

if name == "main": main()

