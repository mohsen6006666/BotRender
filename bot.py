import os import logging import requests from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters )

BOT_TOKEN = os.environ.get("BOT_TOKEN") LOG_CHANNEL_ID = -1002699774923 LOGGED_USERS_FILE = "logged_users.txt" YTS_API_URL = "https://yts.mx/api/v2/list_movies.json"

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

Helper to check if user is already logged

def is_user_logged(user_id): if not os.path.exists(LOGGED_USERS_FILE): return False with open(LOGGED_USERS_FILE, "r") as f: return str(user_id) in f.read()

Helper to log user

def log_user(user): if not is_user_logged(user.id): with open(LOGGED_USERS_FILE, "a") as f: f.write(f"{user.id} - {user.first_name}\n") return True return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user if log_user(user): await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"New user: {user.mention_html()}", parse_mode="HTML")

await update.message.reply_text(
    "Welcome to the Movie Bot!\n\nSend me any movie name and I’ll get torrents with quality options."
)

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.message.text.strip() res = requests.get(YTS_API_URL, params={"query_term": query})

try:
    movies = res.json().get("data", {}).get("movies", [])
    if not movies:
        await update.message.reply_text("No movies found.")
        return

    buttons = []
    for movie in movies[:10]:
        title = f"{movie['title']} ({movie['year']})"
        buttons.append([InlineKeyboardButton(title, callback_data=f"movie_{movie['id']}")])

    await update.message.reply_text(
        "🎥 Select a movie:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

except Exception as e:
    await update.message.reply_text("Something went wrong while searching.")
    logger.error(f"Search error: {e}")

async def movie_selected(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() movie_id = query.data.split("_")[1]

res = requests.get(YTS_API_URL, params={"movie_id": movie_id})
movie = res.json().get("data", {}).get("movie")

if not movie:
    await query.edit_message_text("Could not fetch movie details.")
    return

buttons = []
for torrent in movie.get("torrents", []):
    quality = torrent["quality"]
    hash_ = torrent["hash"]
    buttons.append([
        InlineKeyboardButton(f"{quality}p", callback_data=f"torrent_{hash_}_{movie['title']} ({movie['year']})")
    ])

if not buttons:
    await query.edit_message_text("No quality options found.")
    return

await query.edit_message_text(
    "Choose quality:",
    reply_markup=InlineKeyboardMarkup(buttons)
)

async def send_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() data = query.data.split("", 2) hash = data[1] title = data[2] torrent_url = f"https://yts.mx/torrent/download/{hash_}"

try:
    response = requests.get(torrent_url)
    if response.status_code != 200:
        raise Exception("Torrent not found or expired.")

    with open("temp.torrent", "wb") as f:
        f.write(response.content)

    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=open("temp.torrent", "rb"),
        filename=f"{title}.torrent",
        caption=f"Play on [Webtor.io](https://webtor.io) or use aTorrent.",
        parse_mode="Markdown"
    )
    os.remove("temp.torrent")
except Exception as e:
    await query.edit_message_text("Torrent expired or not found.")
    logger.error(f"Error sending file: {e}")

if name == "main": app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
app.add_handler(CallbackQueryHandler(movie_selected, pattern="^movie_"))
app.add_handler(CallbackQueryHandler(send_torrent, pattern="^torrent_"))

app.run_polling()

