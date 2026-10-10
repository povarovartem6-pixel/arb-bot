# 🤖 Arb Scanner Bot

Telegram-бот для поиска межбиржевого крипто-арбитража **по запросу**.

## ✨ Возможности

- 🔍 Скан 8 бирж: **Binance, Bybit, OKX, HTX, Bitget, MEXC, KuCoin, BingX**
- 💰 Учёт taker-комиссий → «грязный» и «чистый» спред
- 📊 Проверка глубины стакана под размер сделки
- 🚫 Фильтр по 24h объёму
- 📜 История спредов за 24 часа
- 🎛 Управление инлайн-кнопками
- 🔒 Приватный доступ (только ADMIN_ID)
- 🐳 Docker-ready

## 🚀 Быстрый старт

```bash
git clone https://github.com/<твой_ник>/arb-bot.git
cd arb-bot
cp .env.example .env
nano .env   # вставь BOT_TOKEN и ADMIN_ID
pip install -r requirements.txt
python bot.py
```

## 🐳 Docker

```bash
docker compose up -d --build
docker compose logs -f
```

## ⚙️ Конфигурация

| Параметр | Описание | По умолчанию |
|---|---|---|
| `SUPPORTED_EXCHANGES` | Список бирж | 8 топовых |
| `MIN_24H_VOLUME_USDT` | Мин. объём пары | 100 000 |
| `MAX_SYMBOLS_PER_SCAN` | Лимит пар за скан | 500 |
| `EXCHANGE_TIMEOUT` | Таймаут запроса, сек | 20 |

## ⚠️ Важно

- Спред ≠ прибыль. Учитывай комиссии за вывод и риск изменения цены.
- Бот не торгует — только подсвечивает возможности.
- Некоторые биржи могут блокировать по IP.

## 📜 Лицензия

MIT
