from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import requests
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "https://yts.mx/api/v2/list_movies.json?query_term="

def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "Welcome to Movie Search Bot! 🎬\n\n"
        "Just type a movie name, and I'll find the torrent for you.\n"
        "After receiving the torrent file, upload it to webtor.io to stream/download it, or use your torrent downloader."
    )
    update.message.reply_text(welcome_message)

def search_movie(update: Update, context: CallbackContext) -> None:
    query = update.message.text.strip()
    response = requests.get(API_URL + query)
    data = response.json()
    
    if data["data"]["movie_count"] == 0:
        update.message.reply_text("No movies found. Try a different title!")
        return
    
    movies = data["data"]["movies"]
    keyboard = []
    
    for movie in movies:
        keyboard.append([InlineKeyboardButton(f"{movie['title']} ({movie['year']})", callback_data=str(movie['id']))])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Select a movie:", reply_markup=reply_markup)

def movie_selected(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    movie_id = query.data
    response = requests.get(API_URL + movie_id)
    data = response.json()
    
    if "movie" not in data["data"]:
        query.message.reply_text("Sorry, I couldn't find details for this movie.")
        return
    
    movie = data["data"]["movie"]
    torrents = movie.get("torrents", [])
    
    if not torrents:
        query.message.reply_text("No torrents available for this movie.")
        return
    
    torrent_links = "\n".join([f"[{t['quality']}]({t['url']})" for t in torrents])
    query.message.reply_text(f"Here are the available torrents for {movie['title']}:\n{torrent_links}", parse_mode="Markdown")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, search_movie))
    dp.add_handler(CallbackQueryHandler(movie_selected))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
