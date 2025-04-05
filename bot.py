import os import logging import tempfile import requests from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters )

TOKEN = os.getenv("BOT_TOKEN") LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", -1001234567890))  # Replace with your channel ID API_URL = "https://yts.mx/api/v2/list_movies.json?query_term={}"

logged_users = set()

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

START HANDLER

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user if user.id not in logged_users: logged_users.add(user.id) await context.bot.send_message( chat_id=LOG_CHANNEL_ID, text=f"New user started bot: {user.full_name} (@{user.username}, ID: {user.id})" ) await update.message.reply_text("Send me the name of a movie to search for torrents.")

SEARCH HANDLER

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.message.text response = requests.get(API_URL.format(query))

try:
    data = response.json()
    movies = data['data']['movies']
    if not movies:
        raise Exception("No movies found")

    for movie in movies[:3]:  # Limit to top 3 results
        title = movie['title']
        torrents = movie['torrents']
        buttons = []

        for t in torrents:
            btn_text = f"{t['quality']} - {t['type']}"
            callback_data = f"{t['url']}|{title}"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])

        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(f"Select quality for: {title}", reply_markup=markup)

except Exception as e:
    logger.error(f"Search failed: {e}")
    await update.message.reply_text("No torrents found for this movie.")

CALLBACK HANDLER

async def download_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() url, title = query.data.split("|", 1)

try:
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Torrent file download failed")

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(response.content)
        tf_path = tf.name

    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=open(tf_path, 'rb'),
        filename=f"{title}.torrent",
        caption=f"Play it on [Webtor](https://webtor.io) or download using **aTorrent**.",
        parse_mode="Markdown"
    )

except Exception as e:
    logger.error(f"Error sending torrent: {e}")
    await query.edit_message_text("Torrent expired or not found.")

MAIN

if name == 'main': app = Application.builder().token(TOKEN).build() app.add_handler(CommandHandler("start", start)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie)) app.add_handler(CallbackQueryHandler(download_torrent)) logger.info("Bot started...") app.run_polling()

