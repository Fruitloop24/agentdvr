import paho.mqtt.client as mqtt
import requests
import os
import json
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# Load environment variables from .env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))  # Your Telegram ID for admin control
MQTT_BROKER = "mqtt"
MQTT_PORT = 1883
MQTT_TOPIC = "agentdvr/#"

# Store user chat IDs dynamically
CHAT_ID_FILE = "subscribers.json"

def load_chat_ids():
    """Load chat IDs from file"""
    if os.path.exists(CHAT_ID_FILE):
        with open(CHAT_ID_FILE, "r") as f:
            return json.load(f)
    return []

def save_chat_ids(chat_ids):
    """Save chat IDs to file"""
    with open(CHAT_ID_FILE, "w") as f:
        json.dump(chat_ids, f)

def start(update: Update, context: CallbackContext):
    """Handles /start command and registers users"""
    chat_id = update.message.chat_id
    chat_ids = load_chat_ids()

    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        save_chat_ids(chat_ids)
        update.message.reply_text("✅ You are now subscribed to alerts!")
    else:
        update.message.reply_text("⚡ You are already subscribed.")

def stop(update: Update, context: CallbackContext):
    """Handles /stop command and removes users"""
    chat_id = update.message.chat_id
    chat_ids = load_chat_ids()

    if chat_id in chat_ids:
        chat_ids.remove(chat_id)
        save_chat_ids(chat_ids)
        update.message.reply_text("🚫 You have been unsubscribed from alerts.")
    else:
        update.message.reply_text("⚠️ You are not subscribed.")

def remove_user(chat_id):
    """Admin removes a user manually"""
    chat_ids = load_chat_ids()
    if chat_id in chat_ids:
        chat_ids.remove(chat_id)
        save_chat_ids(chat_ids)

def send_telegram_text(message):
    """ Sends a text alert to all subscribed Telegram users """
    chat_ids = load_chat_ids()
    if not chat_ids:
        print("❌ No subscribers.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in chat_ids:
        data = {"chat_id": chat_id, "text": message}
        requests.post(url, data=data)

def on_connect(client, userdata, flags, rc):
    """ Handles connection to MQTT broker """
    if rc == 0:
        print(f"✅ Connected to MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        send_telegram_text("🚀 Telegram bot connected to MQTT and ready for alerts!")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """ Handles incoming MQTT messages """
    print(f"📥 Received MQTT message on topic: {msg.topic}")
    send_telegram_text(f"⚡ Alert from {msg.topic}!\n{msg.payload.decode()}")

def main():
    """ Starts the MQTT client and Telegram bot """
    print("🚀 Starting Telegram Bot...")
    
    # Set up MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    # Start MQTT loop
    client.loop_start()

    # Start Telegram Bot
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

