import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

SUPPORTED_EXCHANGES = [
    "binance",
    "bybit",
    "okx",
    "htx",
    "bitget",
    "mexc",
    "kucoin",
    "bingx",     # вместо gate
]

DEFAULT_TAKER_FEE = 0.001
MIN_24H_VOLUME_USDT = 100_000
MAX_SYMBOLS_PER_SCAN = 500
EXCHANGE_TIMEOUT = 20
