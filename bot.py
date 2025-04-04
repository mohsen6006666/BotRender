import os
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
YTS_API_URL = 'https://yts.mx/api/v2/list_movies.json'

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /search <movie name> to get the .torrent file from YTS.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a movie name.")
        return

    query = ' '.join(context.args)
    response = requests.get(YTS_API_URL, params={'query_term': query})
    data = response.json()

    movies = data.get('data', {}).get('movies', [])
    if not movies:
        await update.message.reply_text("No movies found.")
        return

    movie = movies[0]
    title = movie['title']
    torrents = movie.get('torrents', [])

    if not torrents:
        await update.message.reply_text("No torrent files available.")
        return

    torrent = torrents[0]
    torrent_url = torrent['url']
    file_name = f"{title}.torrent"
    file_path = os.path.join("downloads", file_name)

    os.makedirs("downloads", exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(requests.get(torrent_url).content)

    with open(file_path, 'rb') as f:
        await update.message.reply_document(f, filename=file_name, caption=f"{title} - Torrent File")

    os.remove(file_path)

def start_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("search", search))
    app_bot.run_polling()

if __name__ == '__main__':
    Thread(target=run_web).start()
    start_bot()
