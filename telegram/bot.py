import paho.mqtt.client as mqtt
import requests
import base64
import os
import time
import binascii
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# MQTT Broker Details - Using Docker service name
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt")  # Docker service name from docker-compose
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "agentdvr/#")  # Listen to all agentdvr topics

# Validate required environment variables
if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

def send_telegram_text(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    print(f"Telegram Text Response: {response.json()}")

def send_telegram_image(image_data, source_topic):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        image_path = f"/tmp/mqtt_alert_{int(time.time())}.jpg"
        
        with open(image_path, "wb") as img_file:
            img_file.write(image_data)
        
        # Send both the image and information about its source
        caption = f"Alert image from topic: {source_topic}"
        
        with open(image_path, "rb") as img_file:
            response = requests.post(
                url, 
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, 
                files={"photo": img_file}
            )
        print(f"Telegram Image Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Error sending image to Telegram: {e}")
        return False

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to topic: {MQTT_TOPIC}")
    # Send test message on startup
    send_telegram_text("Telegram bot connected to MQTT broker and ready for alerts!")

def on_message(client, userdata, msg):
    print(f"Received MQTT message on topic: {msg.topic}")
    print(f"Payload length: {len(msg.payload)} bytes")
    
    try:
        # Check if this is one of the image topics from the logs
        if msg.topic == "agentdvr/snapshot" or msg.topic == "agentdvr/image":
            print(f"Processing image from {msg.topic}")
            
            # Try to detect if it's base64 encoded or raw binary
            try:
                # First check if it's base64 text
                if len(msg.payload) > 20:  # Arbitrary small size check
                    start_bytes = msg.payload[:20]
                    # Check if it starts with base64 image markers
                    if b'data:image' in start_bytes or b'/9j/' in start_bytes or b'iVBOR' in start_bytes:
                        print("Detected base64 encoded image")
                        image_data = base64.b64decode(msg.payload)
                    else:
                        # Assume it's already binary data
                        print("Assuming raw binary image data")
                        image_data = msg.payload
                        
                    success = send_telegram_image(image_data, msg.topic)
                    if not success:
                        send_telegram_text(f"Failed to process image from {msg.topic}")
            except binascii.Error:
                print("Not valid base64, treating as raw binary")
                send_telegram_image(msg.payload, msg.topic)
            except Exception as e:
                print(f"Error processing image: {e}")
                send_telegram_text(f"Error processing image from {msg.topic}: {str(e)}")
        else:
            # For non-image topics, send as text
            try:
                payload = msg.payload.decode()
                print(f"Text payload: {payload}")
                send_telegram_text(f"Alert from {msg.topic}!\n{payload}")
            except UnicodeDecodeError:
                # If we can't decode as text, it might be binary data
                print("Payload is not UTF-8 text, might be binary data")
                if len(msg.payload) > 100:  # Arbitrary size to guess if it might be an image
                    try:
                        send_telegram_image(msg.payload, msg.topic)
                    except Exception as e:
                        print(f"Failed to send as image: {e}")
                        send_telegram_text(f"Received binary data on {msg.topic} (payload too large to display)")
                else:
                    # Small binary data, just show hex
                    hex_data = msg.payload.hex()
                    send_telegram_text(f"Binary data received on {msg.topic}: {hex_data[:50]}...")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")
        send_telegram_text(f"Error processing message from {msg.topic}: {str(e)}")

def main():
    print("Starting Telegram Bot...")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Keep trying to connect to MQTT broker
    while True:
        try:
            print(f"Attempting to connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            break
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

    print("Starting MQTT loop...")
    client.loop_forever()

if __name__ == "__main__":
    main()