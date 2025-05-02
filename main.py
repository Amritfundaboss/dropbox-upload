from flask import Flask
import threading
import os
import requests
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DROPBOX_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")

app = Flask(__name__)

@app.route('/')
def home():
    return "Dropbox Upload by AK Bot is running."

def download_and_upload(file_url, file_name):
    r = requests.get(file_url)
    if r.status_code == 200:
        headers = {
            "Authorization": f"Bearer {DROPBOX_TOKEN}",
            "Dropbox-API-Arg": f'{{"path": "/{file_name}", "mode": "add", "autorename": true}}',
            "Content-Type": "application/octet-stream",
        }
        res = requests.post("https://content.dropboxapi.com/2/files/upload", headers=headers, data=r.content)
        return res.status_code == 200
    return False

def handle_file(update: Update, context: CallbackContext):
    file = update.message.document or update.message.video or update.message.audio or update.message.photo[-1]
    file_id = file.file_id
    bot: Bot = context.bot
    telegram_file = bot.get_file(file_id)
    file_url = telegram_file.file_path
    file_name = file.file_unique_id + "_" + (file.file_name if hasattr(file, 'file_name') else "file")

    success = download_and_upload(file_url, file_name)
    if success:
        update.message.reply_text("Uploaded to Dropbox successfully.")
    else:
        update.message.reply_text("Failed to upload.")

def handle_url(update: Update, context: CallbackContext):
    text = update.message.text
    if text.startswith("http"):
        file_name = text.split("/")[-1].split("?")[0]
        success = download_and_upload(text, file_name)
        if success:
            update.message.reply_text("Uploaded to Dropbox from URL.")
        else:
            update.message.reply_text("Upload failed.")
    else:
        update.message.reply_text("Send a valid URL.")

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome to Dropbox Upload by AK! Send a file or link.")

def run_bot():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document | Filters.video | Filters.audio | Filters.photo, handle_file))
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_url))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start()
    run_bot()