import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID") or "0")

# Cheksiz foydalanish huquqiga ega userlar (username — kichik harf)
ADMIN_USERNAMES = {"muhammadjonxp"}
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "8600 XXXX XXXX XXXX")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "Muhammadjon Ne'matov")

PROXY_URL = os.getenv("PROXY_URL") or None

SUBSCRIPTION_PRICE = 10000
SUBSCRIPTION_DAYS = 2

IMAGES_DIR = "images"
os.makedirs(IMAGES_DIR, exist_ok=True)
