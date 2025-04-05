import os import logging import requests from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters )

BOT_TOKEN = os.environ.get("BOT_TOKEN") LOG_CHANNEL_ID = -1002699774923 logged_users = set()

logging.basicConfig(level=logging.INFO)

YTS_API = "https://yts.mx/api/v2/list_movies.json?query_term="

/start command

def get_start_message(): return ( "Hey! Just send me a movie name and I'll try to fetch the available torrent files for you.\n\n" "You can download them or play using Webtor.\n\n" "Example: Oppenheimer or John Wick" )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id if user_id not in logged_users: await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"New user started: {update.effective_user.full_name} (@{update.effective_user.username})") logged_users.add(user_id) await update.message.reply_text(get_start_message(), parse_mode="Markdown", disable_web_page_preview=True)

Search handler

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.message.text.strip() response = requests.get(YTS_API + query) data = response.json()

if data['status'] != 'ok' or not data['data']['movies']:
    await update.message.reply_text("No movies found. Try another title.")
    return

buttons = []
for movie in data['data']['movies'][:10]:
    title = movie['title']
    year = movie['year']
    movie_id = movie['id']
    buttons.append([InlineKeyboardButton(f"{title} ({year})", callback_data=f"movie_{movie_id}")])

reply_markup = InlineKeyboardMarkup(buttons)
await update.message.reply_text("🎥 Select a movie:", reply_markup=reply_markup)

Quality selection

async def movie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer()

movie_id = query.data.split("_")[1]
response = requests.get(f"https://yts.mx/api/v2/movie_details.json?movie_id={movie_id}&with_torrents=true")
data = response.json()

if data['status'] != 'ok' or not data['data']['movie']['torrents']:
    await query.edit_message_text("Torrent expired or not found.")
    return

buttons = []
for torrent in data['data']['movie']['torrents']:
    quality = torrent['quality']
    hash_string = torrent['hash']
    url = f"https://yts.mx/torrent/download/{hash_string}"
    buttons.append([InlineKeyboardButton(quality, url=url)])

reply_markup = InlineKeyboardMarkup(buttons)
await query.edit_message_text("Choose your preferred quality:", reply_markup=reply_markup)

Main function

def main(): app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
app.add_handler(CallbackQueryHandler(movie_callback))

app.run_polling()

if name == 'main': main()

