import asyncio
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, ADMIN_ID, SUPPORTED_EXCHANGES
from db import (init_db, get_settings, save_settings,
                save_history, get_top_history)
from scanner import scan_all

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Middleware приватности ----------
class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is None or user.id != ADMIN_ID:
            if isinstance(event, types.Message):
                await event.answer("⛔ Доступ запрещён.")
            elif isinstance(event, types.CallbackQuery):
                await event.answer("⛔ Доступ запрещён.", show_alert=True)
            return
        return await handler(event, data)

# ---------- Клавиатуры ----------

def kb_main():
    b = InlineKeyboardBuilder()
    b.button(text="📊 Скан", callback_data="scan")
    b.button(text="⚙️ Настройки", callback_data="settings")
    b.button(text="📜 История", callback_data="history")
    b.adjust(2, 1)
    return b.as_markup()

def kb_source(current=None):
    b = InlineKeyboardBuilder()
    for ex in SUPPORTED_EXCHANGES:
        mark = " ✅" if ex == current else ""
        b.button(text=f"{ex}{mark}", callback_data=f"src:{ex}")
    b.adjust(2)
    b.button(text="⬅️ Назад", callback_data="menu")
    return b.as_markup()

def kb_exchanges(selected):
    b = InlineKeyboardBuilder()
    for ex in SUPPORTED_EXCHANGES:
        mark = " ✅" if ex in selected else ""
        b.button(text=f"{ex}{mark}", callback_data=f"tg:{ex}")
    b.button(text="💾 Готово", callback_data="menu")
    b.adjust(2)
    return b.as_markup()

def kb_threshold():
    b = InlineKeyboardBuilder()
    for th in [0.3, 0.5, 1.0, 2.0, 3.0]:
        b.button(text=f"{th}%", callback_data=f"th:{th}")
    b.button(text="⬅️ Назад", callback_data="settings")
    b.adjust(3, 2, 1)
    return b.as_markup()

def kb_trade_size():
    b = InlineKeyboardBuilder()
    for s in [100, 500, 1000, 5000, 10000]:
        b.button(text=f"${s}", callback_data=f"ts:{s}")
    b.button(text="⬅️ Назад", callback_data="settings")
    b.adjust(3, 2, 1)
    return b.as_markup()

def kb_back(to="menu"):
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Назад", callback_data=to)
    return b.as_markup()

# ---------- Хендлеры ----------

@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    text = (
        "👋 <b>Arb Scanner</b>\n\n"
        "Ищу межбиржевой арбитраж по запросу.\n"
        "Учитываю комиссии, объём и глубину стакана.\n\n"
        "Начни с кнопки «Настройки»."
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=kb_main())

@dp.callback_query(F.data == "menu")
async def cb_menu(cb: types.CallbackQuery):
    await cb.message.edit_text("Главное меню", reply_markup=kb_main())
    await cb.answer()

@dp.callback_query(F.data == "settings")
async def cb_settings(cb: types.CallbackQuery):
    s = get_settings(cb.from_user.id)
    if not s or not s[0]:
        text = "Настройки не заданы.\nВыбери биржу-источник 👇"
    else:
        text = (
            f"⚙️ <b>Настройки</b>\n\n"
            f"Источник: <code>{s[0]}</code>\n"
            f"Сравнение: <code>{s[1]}</code>\n"
            f"Порог: <b>{s[2]}%</b>\n"
            f"Размер сделки: <b>${s[3]}</b>\n"
            f"Мин. объём 24h: <b>${s[4]:,.0f}</b>"
        )
    b = InlineKeyboardBuilder()
    b.button(text="🏦 Биржа-источник", callback_data="pick_source")
    b.button(text="🔁 Биржи сравнения", callback_data="pick_exchanges")
    b.button(text="📈 Порог", callback_data="pick_threshold")
    b.button(text="💰 Размер сделки", callback_data="pick_size")
    b.button(text="⬅️ Назад", callback_data="menu")
    b.adjust(1)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=b.as_markup())
    await cb.answer()

@dp.callback_query(F.data == "pick_source")
async def cb_pick_source(cb: types.CallbackQuery):
    s = get_settings(cb.from_user.id)
    current = s[0] if s else None
    await cb.message.edit_text(
        "Выбери биржу, где лежат деньги:",
        reply_markup=kb_source(current)
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("src:"))
async def cb_set_source(cb: types.CallbackQuery):
    ex = cb.data.split(":")[1]
    save_settings(cb.from_user.id, source=ex)
    await cb.answer(f"Источник: {ex}")
    await cb_pick_source(cb)

@dp.callback_query(F.data == "pick_exchanges")
async def cb_pick_exchanges(cb: types.CallbackQuery):
    s = get_settings(cb.from_user.id)
    selected = s[1].split(",") if s and s[1] else []
    await cb.message.edit_text(
        "Отметь биржи для сравнения:",
        reply_markup=kb_exchanges(selected)
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("tg:"))
async def cb_toggle_exchange(cb: types.CallbackQuery):
    ex = cb.data.split(":")[1]
    s = get_settings(cb.from_user.id)
    selected = s[1].split(",") if s and s[1] else []
    if ex in selected:
        selected.remove(ex)
    else:
        selected.append(ex)
    save_settings(cb.from_user.id, exchanges=",".join(selected))
    await cb.answer()
    await cb_pick_exchanges(cb)

@dp.callback_query(F.data == "pick_threshold")
async def cb_pick_threshold(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "Минимальный спред (грязный):",
        reply_markup=kb_threshold()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("th:"))
async def cb_set_threshold(cb: types.CallbackQuery):
    th = float(cb.data.split(":")[1])
    save_settings(cb.from_user.id, threshold=th)
    await cb.answer(f"Порог: {th}%")
    await cb_settings(cb)

@dp.callback_query(F.data == "pick_size")
async def cb_pick_size(cb: types.CallbackQuery):
    await cb.message.edit_text(
        "Размер сделки (для проверки ликвидности):",
        reply_markup=kb_trade_size()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("ts:"))
async def cb_set_size(cb: types.CallbackQuery):
    size = float(cb.data.split(":")[1])
    save_settings(cb.from_user.id, trade_size=size)
    await cb.answer(f"Размер: ${size}")
    await cb_settings(cb)

@dp.callback_query(F.data == "history")
async def cb_history(cb: types.CallbackQuery):
    rows = get_top_history(cb.from_user.id)
    if not rows:
        await cb.message.edit_text("История пуста.", reply_markup=kb_back())
        await cb.answer()
        return
    lines = ["📜 <b>Топ спредов за 24ч</b>\n"]
    for ts, sym, src, tgt, net in rows:
        t = ts[11:19]
        lines.append(f"<code>{t}</code> {sym} {src}→{tgt} <b>+{net:.2f}%</b>")
    await cb.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=kb_back()
    )
    await cb.answer()

@dp.callback_query(F.data == "scan")
async def cb_scan(cb: types.CallbackQuery):
    s = get_settings(cb.from_user.id)
    if not s or not s[0] or not s[1]:
        await cb.answer("Сначала задай источник и биржи", show_alert=True)
        return

    source, exchanges_str, threshold, trade_size, min_volume = s
    target_ids = [e for e in exchanges_str.split(",") if e and e != source]
    if not target_ids:
        await cb.answer("Нет бирж для сравнения", show_alert=True)
        return

    await cb.message.edit_text("🔍 Сканирую все биржи...\n<code>0%</code>", parse_mode="HTML")
    await cb.answer()

    last_edit = 0

    async def progress(done, total, found):
        nonlocal last_edit
        now = time.time()
        if now - last_edit < 2 and done < total:
            return
        last_edit = now
        pct = int(done / total * 100)
        try:
            await cb.message.edit_text(
                f"🔍 Сканирую все биржи...\n"
                f"<code>{pct}%</code> ({done}/{total})\n"
                f"найдено: <b>{found}</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

    try:
        results = await scan_all(source, threshold, trade_size, min_volume, progress_cb=progress)
    except Exception as e:
        await cb.message.edit_text(
            f"❌ Ошибка: <code>{e}</code>", parse_mode="HTML", reply_markup=kb_back()
        )
        return

    now = datetime.now().strftime("%H:%M:%S")
    if not results:
        await cb.message.edit_text(
            f"⏱ <code>{now}</code> — спредов выше {threshold}% нет.",
            parse_mode="HTML", reply_markup=kb_back()
        )
        return

    save_history(cb.from_user.id, results)

    lines = [f"🟢 <b>Найдено: {len(results)}</b> | <code>{now}</code>\n"]
    for r in results[:10]:
        lines.append(
            f"📌 <b>{r['symbol']}</b>\n"
            f"   {r['source']}: <code>${r['s_price']:.6g}</code>\n"
            f"   {r['target']}: <code>${r['t_price']:.6g}</code>\n"
            f"   спред: <b>+{r['gross']:.2f}%</b> → чистыми <b>+{r['net']:.2f}%</b>\n"
        )
    text = "\n".join(lines)[:4000]
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb_back())

async def main():
    init_db()
    dp.message.middleware(AdminOnlyMiddleware())
    dp.callback_query.middleware(AdminOnlyMiddleware())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
