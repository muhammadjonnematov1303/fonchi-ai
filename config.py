import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID") or "0")

ADMIN_USERNAMES = {"muhammadjonxp"}
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "8600 XXXX XXXX XXXX")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "Muhammadjon Nematov")

PROXY_URL = os.getenv("PROXY_URL") or None

COST_PER_IMAGE = 500        # 1 ta rasm uchun so'm
TOPUP_AMOUNT   = 10000      # To'lov tasdiqlanganda qo'shiladigan so'm

IMAGES_DIR = "images"
os.makedirs(IMAGES_DIR, exist_ok=True)