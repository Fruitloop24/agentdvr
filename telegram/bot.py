import os
import json
import base64
import paho.mqtt.client as mqtt
import requests
import logging

# Load environment variables
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "agentdvr/#")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_ID")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram_text(text):
    """Sends a text message to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": ADMIN_CHAT_ID, "text": text}
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        logging.info("Sent message: %s", text)
    except requests.exceptions.RequestException as e:
        logging.error("Telegram text send error: %s", e)

def send_telegram_image(image_data, caption="Alert image"):
    """Sends an image to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("image.jpg", image_data, "image/jpeg")}
    data = {"chat_id": ADMIN_CHAT_ID, "caption": caption}
    try:
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        logging.info("Sent image alert.")
    except requests.exceptions.RequestException as e:
        logging.error("Telegram image send error: %s", e)

def on_connect(client, userdata, flags, rc):
    """Handles MQTT connection."""
    if rc == 0:
        logging.info("Connected to MQTT Broker")
        client.subscribe(MQTT_TOPIC, qos=2)
        logging.info("Subscribed to: %s", MQTT_TOPIC)
        send_telegram_text("Telegram bot connected and ready for alerts!")
    else:
        logging.error("Failed to connect, return code %d", rc)

def on_message(client, userdata, msg):
    """Processes incoming MQTT messages."""
    try:
        payload = msg.payload
        if not payload:
            return
        
        logging.info("Received MQTT message on topic: %s", msg.topic)
        
        if b'data:image' in payload[:20] or b'\xFF\xD8' in payload[:2]:  # JPEG signature
            logging.info("Processing image from topic: %s", msg.topic)
            send_telegram_image(payload, caption=f"Alert image from topic: {msg.topic}")
        else:
            logging.info("Received non-image payload, ignored.")
    except Exception as e:
        logging.error("Error processing MQTT message: %s", e)

def start_bot():
    """Starts the MQTT client."""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.will_set(MQTT_TOPIC, "Bot disconnected unexpectedly!", qos=2, retain=True)
    
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    logging.info("Starting Telegram Listener Bot...")
    start_bot()
