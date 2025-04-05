import os import logging import requests from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile from telegram.ext import ( Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters )

BOT_TOKEN = os.getenv("BOT_TOKEN") LOG_CHANNEL_ID = -1002699774923

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

user_logged = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user if user.id not in user_logged: user_logged.add(user.id) await context.bot.send_message( chat_id=LOG_CHANNEL_ID, text=f"New user started: {user.full_name} (@{user.username}, ID: {user.id})" )

await update.message.reply_text(
    "Send me a movie name and I'll fetch the torrent file for you."
)

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.message.text.strip() if not query: await update.message.reply_text("Please enter a valid movie name.") return

url = f"https://yts.mx/api/v2/list_movies.json?query_term={query}"
response = requests.get(url).json()
movies = response.get("data", {}).get("movies", [])

if not movies:
    await update.message.reply_text("No movies found.")
    return

keyboard = []
for movie in movies:
    title = movie.get("title")
    year = movie.get("year")
    movie_id = movie.get("id")
    keyboard.append([
        InlineKeyboardButton(f"{title} ({year})", callback_data=f"movie_{movie_id}")
    ])

reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text("🎥 Select a movie:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer()

if query.data.startswith("movie_"):
    movie_id = query.data.split("_")[1]
    url = f"https://yts.mx/api/v2/movie_details.json?movie_id={movie_id}&with_torrents=true"
    response = requests.get(url).json()
    movie = response.get("data", {}).get("movie", {})

    torrents = movie.get("torrents", [])
    if not torrents:
        await query.edit_message_text("Torrent expired or not found.")
        return

    keyboard = []
    for tor in torrents:
        quality = tor.get("quality")
        hash_string = tor.get("hash")
        magnet_link = f"magnet:?xt=urn:btih:{hash_string}"
        keyboard.append([
            InlineKeyboardButton(quality, url=magnet_link)
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Choose quality:", reply_markup=reply_markup)

if name == 'main': app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()

