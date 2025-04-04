import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# Store search results in memory for each user
user_search_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /search <movie name> to find a YTS torrent.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Please provide a movie name. Example: /search Interstellar")
        return

    url = f"https://yts.mx/api/v2/list_movies.json?query_term={query}"
    response = requests.get(url).json()

    movies = response.get("data", {}).get("movies", [])

    if not movies:
        await update.message.reply_text("No movies found.")
        return

    # Save movie data to handle button clicks
    user_id = update.effective_user.id
    user_search_data[user_id] = movies

    keyboard = []
    for i, movie in enumerate(movies):
        title = f"{movie['title']} ({movie['year']})"
        keyboard.append([InlineKeyboardButton(title, callback_data=str(i))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a movie:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    movies = user_search_data.get(user_id, [])

    index = int(query.data)
    if index >= len(movies):
        await query.edit_message_text("Invalid selection.")
        return

    movie = movies[index]
    torrents = movie.get("torrents", [])
    if not torrents:
        await query.edit_message_text("No torrents found for this movie.")
        return

    torrent_url = torrents[0].get("url")
    title = f"{movie['title']} ({movie['year']})"
    await query.edit_message_text(f"Sending torrent for: {title}")
    await context.bot.send_document(chat_id=query.message.chat_id, document=torrent_url)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.run_polling()
