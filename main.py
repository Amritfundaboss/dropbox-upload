from flask import Flask, request
import os
import requests
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DROPBOX_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Should be set in Render env variables

app = Flask(__name__)
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

@app.route('/')
def home():
    return "Dropbox Upload by AK Bot (Webhook) is running."

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

def download_and_upload(file_url, file_name):
    r = requests.get(file_url)
    if r.status_code == 200:
        headers = {
            "Authorization": f"Bearer {DROPBOX_TOKEN}",
            "Dropbox-API-Arg": f'{{"path": "/{file_name}", "mode": "add", "autorename": true}}',
            "Content-Type": "application/octet-stream",
        }
        res = requests.post("https://content.dropboxapi.com/2/files/upload", headers=headers, data=r.content)
        print("Dropbox response:", res.status_code, res.text)
        return res.status_code == 200
    return False

def handle_file(update, context):
    file = update.message.document or update.message.video or update.message.audio or update.message.photo[-1]
    file_id = file.file_id
    telegram_file = context.bot.get_file(file_id)
    file_url = telegram_file.file_path
    file_name = file.file_unique_id + "_" + (file.file_name if hasattr(file, 'file_name') else "file")
    success = download_and_upload(file_url, file_name)
    if success:
        update.message.reply_text("Uploaded to Dropbox successfully.")
    else:
        update.message.reply_text("Failed to upload.")

def handle_url(update, context):
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

def start(update, context):
    update.message.reply_text("Welcome to Dropbox Upload by AK! Send a file or link.")

# Register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.document | Filters.video | Filters.audio | Filters.photo, handle_file))
dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_url))

if __name__ == "__main__":
    bot.set_webhook(f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    app.run(host="0.0.0.0", port=8080)