# -*- coding: utf-8 -*-
import asyncio
import sqlite3
import random
import os
import re

def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")

db = sqlite3.connect("balances.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS balances (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER NOT NULL
)
""")
db.commit()

cur.execute("""
CREATE TABLE IF NOT EXISTS untop (
    user_id INTEGER PRIMARY KEY
)
""")
db.commit()

cur.execute("""
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY
)
""")
db.commit()

import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    uid INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")

conn.commit()

import sqlite3
import time

from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.types import Dice
import time
from collections import defaultdict, deque
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandObject
from aiogram import F


TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 5338814259
SUPPORT_ID = 7931101383

LOG_FILE = "logs.txt"
USERS_FILE = "users.txt"

BONUS_TIME = 12 * 60 * 60
CURRENCY = "playks"

bonus_cd = {}
pending_transfers = {}

bot = Bot(TOKEN)
dp = Dispatcher()

miners = {}
card_games = {}

#---------- ШАБЛОН СТАРТА ----------

from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardRemove

@dp.message(CommandStart())
async def start(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    add_user(uid)

    me = await bot.me()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Чат",
                url=f"https://t.me/{me.username}?startgroup=true"
            ),
            InlineKeyboardButton(
                text="👤 Поддержка",
                url="tg://openmessage?user_id=7931101383"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏢 База",
                url="https://t.me/kplaybase"
            ),
            InlineKeyboardButton(
                text="📢 Канал",
                url="https://t.me/kplaynews"
            )
        ],
        [
            InlineKeyboardButton(
                text="📜 Все команды",
                url="https://t.me/kplaybase/26"
            )
        ]
    ])

    await message.answer(
        "👋 Привет, я Kplay - бот для игр 🎮\n\n"
        "👑 Поддержка:\n"
        "@Kplay_support\n\n"
        "📜 Команды:\n"
        "• Б / баланс — баланс\n"
        "• Бонус — бонус (12ч)\n"
        "• 100 красное / красное 100\n"
        "• 100 черное / черное 100\n"
        "• 100 орел / орел 100\n"
        "• 100 решка / решка 100\n"
        "• Сапер 100\n"
        "• Карты 100\n"
        "• Куб / кубик\n"
        "• Баскетбол / Баскет\n"
        "• Казино, казик, спин, 777, деп, рулетка, крутилка\n"
        "• Топ, балансы\n"
        "• Антоп / бектоп (антоп убирает ссылку на твой профиль из топа)\n"
        "• Промокод / промо (название промокода)\n\n"
        "Канал @kplaynews",
        reply_markup=kb
    )

# ---------- ЛОГ ----------

def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {text}\n")

# ---------- USERS ----------

def add_user(uid):
    uid = str(uid)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(uid + "\n")
        return

    with open(USERS_FILE, "r") as f:
        users = set(x.strip() for x in f if x.strip())

    if uid not in users:
        with open(USERS_FILE, "a") as f:
            f.write(uid + "\n")

def get_all_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return [int(x.strip()) for x in f if x.strip().isdigit()]

#--------------- КД ------------

SPAM_LIMIT = 3        # сообщений
SPAM_INTERVAL = 4    # секунд
SPAM_MUTE = 2        # секунд

user_messages = defaultdict(lambda: deque())
user_muted_until = {}

from aiogram.dispatcher.middlewares.base import BaseMiddleware

class AntiSpamMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not isinstance(event, types.Message):
            return await handler(event, data)

        uid = event.from_user.id
        now = time.time()

        if uid in user_muted_until and user_muted_until[uid] > now:
            return  # ❗ тихо блокируем, но НЕ жрём хендлеры

        q = user_messages[uid]
        while q and now - q[0] > SPAM_INTERVAL:
            q.popleft()

        q.append(now)

        if len(q) >= SPAM_LIMIT:
            user_muted_until[uid] = now + SPAM_MUTE
            q.clear()
            return

        return await handler(event, data)
        
dp.message.middleware(AntiSpamMiddleware())
   
# ---------- БАЛАНС ----------

import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")
conn.commit()


def add_user(user_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()


def get_balance(user_id: int) -> int:
    add_user(user_id)

    cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()

    return result[0] if result else 0


def add_balance(user_id: int, amount: int):
    add_user(user_id)

    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()


@dp.message(lambda m: m.text and m.text.lower() in ["б", "баланс", "/b", "/bal", "/balance", "балик", "бал"])
async def balance_cmd(msg: types.Message):
    user_id = msg.from_user.id
    bal = get_balance(user_id)
    await msg.reply(f"💰 Баланс: {fmt(bal)} {CURRENCY}")
    
# ---------- БОНУС ----------

@dp.message(lambda m: m.text and m.text.lower() in  ["бонус", "/bonus"])
async def bonus(msg: types.Message):
    add_user(msg.from_user.id)
    uid = msg.from_user.id
    now = int(datetime.now().timestamp())

    last = bonus_cd.get(uid, 0)
    if now - last < BONUS_TIME:
        wait = BONUS_TIME - (now - last)
        h = wait // 3600
        m = (wait % 3600) // 60
        await msg.reply(f"⏳ Бонус через {h}ч {m}м")
        return

    bonus_cd[uid] = now
    add_balance(uid, 3000)
    bal = get_balance(uid)
    await msg.reply(f"🎁 +3000 {CURRENCY}")

#-------------------- СМАЙЛЫ ЛУДКИ -----------

@dp.message(lambda m: m.text and m.text.lower() in ["куб", "кубик", "/cube"])
async def dice_game(msg: types.Message):
    await msg.reply_dice(emoji="🎲")
    
@dp.message(lambda m: m.text and m.text.lower() in ["баскет", "баскетбол", "/basket", "/basketball"])
async def basket_game(msg: types.Message):
    await msg.reply_dice(emoji="🏀")


@dp.message(lambda m: m.text and m.text.lower() in [
    "казино", "казик", "спин", "777", "деп", "рулетка", "крутилка", "/spin", "/dep", "/777", "/casino"
])
async def casino_game(msg: types.Message):
    await msg.reply_dice(emoji="🎰")

#-------------- ПРОСТЫЕ ОТВЕТЫ ----------------

@dp.message(lambda m: m.text and m.text.lower() == "пиу")
async def cmd_piu(msg: types.Message):
    await msg.reply("Пау")

@dp.message(lambda m: m.text and m.text.lower() == "пинг")
async def cmd_ping(msg: types.Message):
    await msg.reply("Понг")

@dp.message(lambda m: m.text and m.text.lower() == "до")
async def cmd_do(msg: types.Message):
    await msg.reply("Дооооо")
    
@dp.message(lambda m: m.text and m.text.lower() == "бот")
async def cmd_botik(msg: types.Message):
    await msg.reply("Я тут")

#------------- ПОКУПКА ВАЛЮТЫ -------------

from aiogram.types import LabeledPrice
from aiogram.enums import ChatType

@dp.message(lambda m: m.text and m.text.lower().startswith(("купить", "/buy")))
async def buy_currency(msg: types.Message):

    parts = msg.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        return await msg.reply("❌ Формат: купить 1")

    stars = int(parts[1])

    if stars <= 0:
        return await msg.reply("❌ Минимум 1 ⭐")

    if stars > 10000:
        return await msg.reply("❌ Если сумма больше 10.000 обратитесь в @kplay_support")

    amount_currency = stars * 500

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Купить", callback_data=f"buy_yes:{stars}")
    kb.button(text="❌ Отмена", callback_data="buy_no")
    kb.adjust(2)

    await msg.reply(
        f"💳 Покупка валюты\n\n"
        f"⭐ Звёзды: {stars}\n"
        f"💰 Получите: {amount_currency:,} {CURRENCY}\n"
        f"📈 Курс: 1 ⭐ = 500 {CURRENCY}",
        reply_markup=kb.as_markup()
    )
    
@dp.callback_query(lambda c: c.data.startswith("buy_yes"))
async def buy_confirm(call: types.CallbackQuery):
    stars = int(call.data.split(":")[1])

    await call.message.delete()

    await bot.send_invoice(
        chat_id=call.from_user.id,
        title="💰 Покупка валюты",
        description=f"{stars} ⭐ → {stars * 500} {CURRENCY}",
        payload=f"buy_{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Покупка валюты", amount=stars)],
    )
    
@dp.callback_query(lambda c: c.data == "buy_no")
async def buy_cancel(call: types.CallbackQuery):
    await call.message.edit_text("❌ Покупка отменена")
    
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(lambda m: m.successful_payment)
async def successful_payment(msg: types.Message):
    payload = msg.successful_payment.invoice_payload

    if payload.startswith("buy_"):
        stars = int(payload.split("_")[1])
        currency_amount = stars * 500

        add_balance(msg.from_user.id, currency_amount)

        await msg.answer(
            f"✅ Оплата прошла успешно!\n\n"
            f"💰 Вам начислено: {currency_amount:,} {CURRENCY}\n"
            f"Спасибо за покупку ⭐"
        )

#--------------- ПРОМОКОДЫ -----------

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS promocodes (
    name TEXT PRIMARY KEY,
    amount INTEGER,
    uses_left INTEGER,
    expires_at INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promo_used (
    user_id INTEGER,
    promo_name TEXT,
    PRIMARY KEY (user_id, promo_name)
)
""")

conn.commit()

def create_promo(name, amount, uses):
    conn = sqlite3.connect("database.db") 
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO promocodes 
        (name, amount, uses_left, expires_at)
        VALUES (?, ?, ?, NULL)
    """, (name.lower(), amount, uses))

    conn.commit()
    conn.close()

@dp.message(F.text.startswith("+промо"))
async def add_promo(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split()

    if len(args) != 4:
        await message.answer(
            "❌ Формат:\n"
            "+промо название сумма количество"
        )
        return

    _, name, amount_str, uses_str = args

    # проверка суммы
    try:
        amount = int(amount_str)
    except:
        await message.answer("❌ Сумма должна быть числом")
        return

    # проверка количества
    try:
        uses = int(uses_str)
    except:
        await message.answer("❌ Количество должно быть числом")
        return

    if uses <= 0:
        await message.answer("❌ Количество должно быть больше 0")
        return

    create_promo(name, amount, uses)

    await message.answer(
        f"✅ Промокод {name} создан\n"
        f"💰 Сумма: {amount}\n"
        f"📦 Активаций: {uses}"
    )
        
@dp.message(F.text.startswith("-промо"))
async def delete_promo(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    try:
        _, name = message.text.split()
        name = name.lower()

        cursor.execute("SELECT name FROM promocodes WHERE name=?", (name,))
        promo = cursor.fetchone()

        if not promo:
            await message.answer("❌ Промокод не найден")
            return

        cursor.execute("DELETE FROM promocodes WHERE name=?", (name,))
        conn.commit()

        await message.answer(f"🗑 Промокод {name} удалён")

    except:
        await message.answer("❌ Формат: -промо название")
        
from datetime import datetime

@dp.message(F.text.lower().in_(["промокоды", "промы"]))
async def list_promos(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    cursor.execute("SELECT name, uses_left, expires_at FROM promocodes")
    promos = cursor.fetchall()

    if not promos:
        await message.answer("❌ Промокодов нет")
        return

    text = "📋 Список промокодов:\n\n"

    for name, uses_left, expires_at in promos:
        if uses_left is not None:
            text += f"{name} | {uses_left} активаций\n"
        elif expires_at is not None:
            dt = datetime.fromtimestamp(expires_at)
            formatted = dt.strftime("%d.%m.%Y %H:%M")
            text += f"{name} | {formatted}\n"
        else:
            text += f"{name} | Без ограничений\n"

    await message.answer(text)
        
@dp.message(F.text.lower().startswith(("промо", "промокод")))
async def activate_promo(message: types.Message):
    try:
        parts = message.text.split()
        name = parts[1].lower()
    except:
        await message.answer("❌ Укажите название промокода")
        return

    cursor.execute("SELECT * FROM promocodes WHERE name=?", (name,))
    promo = cursor.fetchone()

    if not promo:
        await message.answer("❌ Промокод не найден")
        return

    name, amount, uses_left, expires_at = promo
    uid = message.from_user.id

    # проверка использовал ли
    cursor.execute("SELECT * FROM promo_used WHERE user_id=? AND promo_name=?", (uid, name))
    if cursor.fetchone():
        await message.answer("❌ Вы уже использовали этот промокод")
        return

    # проверка срока
    if expires_at and int(time.time()) > expires_at:
        await message.answer("❌ Срок действия промокода истек")
        return

    # проверка количества
    if uses_left is not None:
        if uses_left <= 0:
            await message.answer("❌ Лимит активаций исчерпан")
            return

        cursor.execute(
            "UPDATE promocodes SET uses_left = uses_left - 1 WHERE name=?",
            (name,)
        )

    # начисление
    add_balance(uid, amount)

    cursor.execute(
        "INSERT INTO promo_used VALUES (?, ?)",
        (uid, name)
    )

    conn.commit()

    await message.answer(f"🎉 Промокод активирован!\n+{amount} playks")
   
# -------------------- 50/50 -------------------------

@dp.message(
    lambda m: m.text
    and len(m.text.split()) == 2
    and m.text.lower().replace("ё", "е").split()[0] in {
        "орел", "решка", "красное", "черное"
    }
)
async def game_5050(msg: types.Message):
    text = msg.text.lower().replace("ё", "е").split()
    choice, amount = text

    if not amount.isdigit():
        return

    bet = int(amount)

    coin_choices = ["орел", "решка"]
    color_choices = ["красное", "черное"]

    uid = msg.from_user.id
    add_user(uid)

    if get_balance(uid) < bet:
        return await msg.reply("❌ Недостаточно средств")

    # ---------- МОНЕТКА ----------
    if choice in coin_choices:
        add_balance(uid, -bet)
        result = random.choice(coin_choices)

        if choice == result:
            win = bet * 2
            add_balance(uid, win)
            await msg.reply(f"🪙 Выпало: {result}\n🎉 +{fmt(win)} {CURRENCY}")
        else:
            await msg.reply(f"🪙 Выпало: {result}\n💥 Проигрыш")
        return

    # ---------- КРАСНОЕ / ЧЕРНОЕ ----------
    if choice in color_choices:
        add_balance(uid, -bet)
        result = random.choice(color_choices)

        if choice == result:
            win = bet * 2
            add_balance(uid, win)
            await msg.reply(f"🎰 Выпало: {result}\n🎉 +{fmt(win)} {CURRENCY}")
        else:
            await msg.reply(f"🎰 Выпало: {result}\n💥 Проигрыш")
        return
        
# ---------- САПЁР ----------

@dp.message(lambda m: m.text and re.fullmatch(r"(сапер|сапёр)\s+\d+", m.text.lower()))
async def miner(msg: types.Message):
    add_user(msg.from_user.id)
    bet = int(msg.text.split()[1])
    uid = msg.from_user.id

    if get_balance(uid) < bet:
        await msg.reply("❌ Недостаточно средств")
        return

    add_balance(uid, -bet)

    mines = set(random.sample(range(25), 5))
    miners[uid] = {"bet": bet, "mult": 1.0, "mines": mines, "open": set()}

    kb = InlineKeyboardBuilder()
    for i in range(25):
        kb.button(text="⬜", callback_data=f"s_{i}_{uid}")
    kb.button(text="💰 Забрать", callback_data=f"s_cash_{uid}")
    kb.adjust(5)

    await msg.reply(
        f"💣 Сапёр\nСтавка: {bet} {CURRENCY}\nМножитель: 1.0x",
        reply_markup=kb.as_markup()
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("s_"))
async def miner_click(call: types.CallbackQuery):
    await call.answer()

    _, action, owner = call.data.split("_")
    owner = int(owner)

    if call.from_user.id != owner:
        return

    if owner not in miners:
        return

    game = miners[owner]

    if action == "cash":
        win = int(game["bet"] * game["mult"])
        add_balance(owner, win)
        del miners[owner]
        await call.message.edit_text(f"🏆 Ты забрал приз\n+{fmt(win)} {CURRENCY}")
        return

    idx = int(action)

    if idx in game["open"]:
        return

    if idx in game["mines"]:
        del miners[owner]
        await call.message.edit_text("💥 БАХ!")
        return

    game["open"].add(idx)

    # 🎲 Новый баланс множителя
    if random.random() < 0.6:
        game["mult"] += 0.1
    else:
        game["mult"] += 0.2

    kb = InlineKeyboardBuilder()
    for i in range(25):
        if i in game["open"]:
            kb.button(text="🟩", callback_data="x")
        else:
            kb.button(text="⬜", callback_data=f"s_{i}_{owner}")

    kb.button(text="💰 Забрать", callback_data=f"s_cash_{owner}")
    kb.adjust(5)

    await call.message.edit_text(
        f"💣 Сапёр\nМножитель: {game['mult']:.1f}x",
        reply_markup=kb.as_markup()
    )

#--------------- КАРТЫ -----------------

@dp.message(lambda m: m.text and re.fullmatch(r"карты\s+\d+", m.text.lower()))
async def start_card_game(msg: types.Message):
    add_user(msg.from_user.id)

    uid = msg.from_user.id
    bet = int(msg.text.split()[1])

    if get_balance(uid) < bet:
        await msg.reply("❌ Недостаточно средств")
        return

    add_balance(uid, -bet)

    card_games[uid] = {
        "bet": bet,
        "stage": 0,
        "mult": 1.0,
        "history": []
    }

    kb = InlineKeyboardBuilder()
    for i in range(3):
        kb.button(text="🃏", callback_data=f"card_{i}_{uid}")
    kb.button(text="💰 Забрать", callback_data=f"card_cash_{uid}")
    kb.adjust(3,1)

    await msg.reply(
        f"🃏 Партия началась \n"
        f"Раунд: 1/5\n"
        f"Множитель: 1.0x",
        reply_markup=kb.as_markup()
    )
    
@dp.callback_query(lambda c: c.data.startswith("card_"))
async def card_click(call: types.CallbackQuery):
    await call.answer()

    parts = call.data.split("_")

    action = parts[1]
    uid = int(parts[2])

    # 🔒 ЗАЩИТА — ТОЛЬКО ВЛАДЕЛЕЦ ИГРЫ
    if call.from_user.id != uid:
        await call.answer("❌ Это не твоя игра", show_alert=True)
        return

    game = card_games.get(uid)
    if not game:
        return

    # 💰 ЗАБРАТЬ
    if action == "cash":
        win = int(game["bet"] * game["mult"])
        add_balance(uid, win)
        del card_games[uid]       
        await call.message.edit_text(
            f"💰 Ты забрал приз\n"
            f"Выигрыш: {fmt(win)} {CURRENCY}"
        )
        return

    idx = int(parts[1])
    uid = int(parts[2])

    if call.from_user.id != uid:
        return

    game = card_games.get(uid)
    if not game:
        return

    death = random.randint(0, 2)

    row = []
    alive = True
    for i in range(3):
        if i == death:
            row.append("💀")
        else:
            row.append("✅")

    game["history"].append(row)

    if idx == death:
        text = "💥 Проигрыш!\n\n"
        for r in game["history"]:
            text += " ".join(f"[{x}]" for x in r) + "\n"

        await call.message.edit_text(text)
        del card_games[uid]
        return

    # ✅ ПРОШЁЛ
    game["stage"] += 1
    game["mult"] *= 1.2

    if game["stage"] >= 5:
        win = int(game["bet"] * game["mult"])
        add_balance(uid, win)
        await call.message.edit_text(
            f"🏆 5/5\n"
            f"💰 Выигрыш: {win} {CURRENCY}"
        )
        del card_games[uid]
        return

    text = ""
    for r in game["history"]:
        text += " ".join(f"[{x}]" for x in r) + "\n"
    text += "\n" + " ".join("[🃏]" for _ in range(3))

    kb = InlineKeyboardBuilder()
    for i in range(3):
        kb.button(text="🃏", callback_data=f"card_{i}_{uid}")
    kb.button(text="💰 Забрать", callback_data=f"card_cash_{uid}")
    kb.adjust(3,1)

    await call.message.edit_text(
        f"{text}\n\n"
        f"Раунд: {game['stage'] + 1}/5\n"
        f"Множитель: {game['mult']:.2f}x",
        reply_markup=kb.as_markup()
    )

# --------------------- ТОП ------------------------

@dp.message(lambda m: m.text and m.text.lower() in [
    "топ", "/top", "/stat", "балансы", "/baltop"
])
async def show_top(msg: types.Message):
    rows = cur.execute(
    "SELECT user_id, balance FROM balances WHERE user_id NOT IN (?, ?) AND balance > 0 ORDER BY balance DESC LIMIT 10",
    (OWNER_ID, SUPPORT_ID)
).fetchall()

    if not rows:
        return await msg.reply("🏆 Топ пуст")

    hidden = {
        x[0] for x in cur.execute("SELECT user_id FROM untop").fetchall()
    }

    text = "🏆 <b>Топ балансов</b>\n\n"

    for i, (uid, bal) in enumerate(rows, 1):
        bal = fmt(bal)

        if uid in hidden:
            # 👁 скрыт
            line = f"{i}. {uid} [👁] — {bal} {CURRENCY}\n"
        else:
            # 👤 обычный
            line = (
                f'{i}. <a href="tg://openmessage?user_id={uid}">{uid}</a> '
                f"— {bal} {CURRENCY}\n"
            )

        text += line

    await msg.reply(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    
#------- антоп --------

@dp.message(lambda m: m.text and m.text.lower() in ["/untop", "антоп"])
async def untop_cmd(msg: types.Message):
    uid = msg.from_user.id

    cur.execute(
        "INSERT OR IGNORE INTO untop (user_id) VALUES (?)",
        (uid,)
    )
    db.commit()

    await msg.reply("🙈 Ты скрыт в топе\nТвой профиль больше не будет ссылкой")
    
@dp.message(lambda m: m.text and m.text.lower() in ["/backtop", "бектоп"])
async def backtop_cmd(msg: types.Message):
    uid = msg.from_user.id

    cur.execute(
        "DELETE FROM untop WHERE user_id = ?",
        (uid,)
    )
    db.commit()

    await msg.reply("👀 Ты снова отображаешься в топе с ссылкой на профиль")
    
# ---------- ВЫДАТЬ / СНЯТЬ ----------

def user_label(user: types.User):
    return f"@{user.username}" if user.username else str(user.id)

@dp.message(lambda m: m.text and m.text.lower().startswith("выдать"))
async def give(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return

    parts = msg.text.lower().split()

    # ---------- выдать 1000 всем ----------
    if len(parts) == 3 and parts[2] == "всем":
        amount = int(parts[1])
        count = 0

        for uid in get_all_users():
            if uid != msg.from_user.id:
                add_balance(uid, amount)
                count += 1

        await msg.reply(
            f"🛡 Админ KPlay выдал всем юзерам бота {amount} {CURRENCY}\n"
            f"👥 Получили: {count}"
        )
        return

    # ---------- ответом ----------
    if msg.reply_to_message and len(parts) == 2:
        amount = int(parts[1])
        user = msg.reply_to_message.from_user
        add_balance(user.id, amount)
        await msg.reply(
            f"🛡 Админ KPlay выдал {amount} {CURRENCY} {user_label(user)}"
        )
        return

    # ---------- выдать 1000 id ----------
    if len(parts) == 3 and parts[2].isdigit():
        amount = int(parts[1])
        uid = int(parts[2])
        add_balance(uid, amount)
        await msg.reply(
            f"🛡 Админ KPlay выдал {amount} {CURRENCY} {uid}"
        )

@dp.message(lambda m: m.text and m.text.lower().startswith("снять"))
async def take(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return

    parts = msg.text.split()

    if msg.reply_to_message and len(parts) == 2:
        amount = int(parts[1])
        user = msg.reply_to_message.from_user
        add_balance(user.id, -amount)
        await msg.reply(f"🛡 Админ KPlay снял {amount} {CURRENCY} у {user_label(user)}")
        return

    if len(parts) == 3:
        amount = int(parts[1])
        uid = int(parts[2])
        add_balance(uid, -amount)
        await msg.reply(f"🛡 Админ KPlay снял {amount} {CURRENCY} у {uid}")

# ---------- ПЕРЕДАЧА (п 100) ----------

@dp.message()
async def transfer(msg: types.Message):
    if not msg.text:
        return

    text = msg.text.lower().split()

    if text[0] != "отдать":
        return

    if len(text) < 2 or not text[1].isdigit():
        await msg.reply("❌ Пример: Отдать 10000 (ответом на сообщение)")
        return

    if not msg.reply_to_message:
        await msg.reply("❌ Используй команду ответом на сообщение")
        return

    sender = msg.from_user
    receiver = msg.reply_to_message.from_user
    if receiver.id == OWNER_ID:
        return await msg.reply("❌ Админу переводить нельзя")
    amount = int(text[1])

    if receiver.is_bot:
        await msg.reply("❌ Боту нельзя передавать валюту")
        return

    if sender.id == receiver.id:
        await msg.reply("❌ Нельзя передать самому себе")
        return

    if amount <= 0:
        await msg.reply("❌ Сумма должна быть больше 0")
        return

    if get_balance(sender.id) < amount:
        await msg.reply("❌ Недостаточно средств")
        return

    # 🔹 МАЛАЯ СУММА — БЕЗ ПОДТВЕРЖДЕНИЯ
    if amount < 10_000:
        add_balance(sender.id, -amount)
        add_balance(receiver.id, amount)

        await msg.reply(
            f"💸 {user_label(sender)} передал {fmt(amount)} {CURRENCY} {user_label(receiver)}"
        )
        return

    # 🔹 ПОДТВЕРЖДЕНИЕ
    tid = f"{sender.id}:{receiver.id}:{amount}"

    pending_transfers[tid] = {
        "from": sender.id,
        "to": receiver.id,
        "amount": amount
    }

    from_name = f"@{sender.username}" if sender.username else f"ID {sender.id}"
    to_name = f"@{receiver.username}" if receiver.username else f"ID {receiver.id}"

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"pay_yes:{tid}")
    kb.button(text="❌ Отмена", callback_data=f"pay_no:{tid}")
    kb.adjust(2)

    await msg.reply(
        f"⚠️ *Подтверждение операции*\n\n"
        f"💸 Сумма: `{fmt(amount)}`\n"
        f"👤 Отправитель: {from_name}\n"
        f"🎯 Получатель: {to_name}\n\n"
        f"Вы уверены?",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    
@dp.callback_query(lambda c: c.data.startswith("pay_yes:"))
async def confirm_pay(call: types.CallbackQuery):
    tid = call.data.split(":", 1)[1]

    data = pending_transfers.get(tid)
    if not data:
        await call.answer("❌ Операция не найдена", show_alert=True)
        return

    if call.from_user.id != data["from"]:
        await call.answer("❌ Это не ваша операция", show_alert=True)
        return

    if get_balance(data["from"]) < data["amount"]:
        await call.message.edit_text("❌ Недостаточно средств")
        pending_transfers.pop(tid, None)
        return

    add_balance(data["from"], -data["amount"])
    add_balance(data["to"], data["amount"])

    pending_transfers.pop(tid, None)

    await call.message.edit_text(
        f"✅ Перевод выполнен\n"
        f"💸 {fmt(data['amount'])}"
    )

    await call.answer()
    
@dp.callback_query(lambda c: c.data.startswith("pay_no:"))
async def cancel_pay(call: types.CallbackQuery):
    tid = call.data.split(":", 1)[1]

    data = pending_transfers.get(tid)
    if not data:
        await call.answer("❌ Уже отменено", show_alert=True)
        return

    if call.from_user.id != data["from"]:
        await call.answer("❌ Это не ваша операция", show_alert=True)
        return

    pending_transfers.pop(tid, None)

    await call.message.edit_text("❌ Перевод отменён")
    await call.answer()
    
#--------------- ФИКС "алала 7" ------------

import re
from aiogram import types

# все игровые команды, которые принимают ставку
GAME_COMMANDS = {
    "карты",
    "сапер",
    "красное",
    "черное",
    "орел",
    "решка"
}

def parse_bet(text: str):
    if not text:
        return None, None

    text = text.lower().replace("ё", "е").strip()

    for cmd in GAME_COMMANDS:
        m = re.fullmatch(rf"{cmd}\s+(\d+)", text)
        if m:
            return cmd, int(m.group(1))

    return None, None


@dp.message()
async def universal_games(msg: types.Message):
    cmd, bet = parse_bet(msg.text)

    if not cmd:
        return  # ❗ НЕ ИГРА — НЕ ЛОМАЕМ ДРУГИЕ КОМАНДЫ

    if bet <= 0:
        return await msg.reply("❌ Ставка должна быть больше 0")

    # ⬇️ РАСКИДЫВАЙ ПО СВОИМ ФУНКЦИЯМ
    if cmd == "карты":
        await play_cards(msg, bet)

    elif cmd == "сапер":
        await play_mines(msg, bet)

    elif cmd in ("красное", "черное", "орел", "решка"):
        await play_roulette(msg, cmd, bet)

# ---------- ЗАПУСК ----------

from aiohttp import web
import asyncio
from aiogram.types import ReplyKeyboardRemove

async def handle(request):
    return web.Response(text="ВСЕ РАБОТАЕТ")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

async def main():
    log("Bot started")
    await start_web()
    await dp.start_polling(bot)

if __name__ == "__main__":
 asyncio.run(main())
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    uid INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")

conn.commit()

import sqlite3
import time

from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.types import Dice
import time
from collections import defaultdict, deque
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandObject
from aiogram import F


TOKEN = "8597055165:AAEr5JFC-7MHdGZwS8hgZL82CVwEUSBpeA4"
OWNER_ID = 5338814259
SUPPORT_ID = 7931101383

LOG_FILE = "logs.txt"
USERS_FILE = "users.txt"

BONUS_TIME = 12 * 60 * 60
CURRENCY = "playks"

bonus_cd = {}
pending_transfers = {}

bot = Bot(TOKEN)
dp = Dispatcher()

miners = {}
card_games = {}

#---------- ШАБЛОН СТАРТА ----------

from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardRemove

@dp.message(CommandStart())
async def start(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    add_user(uid)

    me = await bot.me()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Чат",
                url=f"https://t.me/{me.username}?startgroup=true"
            ),
            InlineKeyboardButton(
                text="👤 Поддержка",
                url="tg://openmessage?user_id=7931101383"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏢 База",
                url="https://t.me/kplaybase"
            ),
            InlineKeyboardButton(
                text="📢 Канал",
                url="https://t.me/kplaynews"
            )
        ],
        [
            InlineKeyboardButton(
                text="📜 Все команды",
                url="https://t.me/kplaybase/26"
            )
        ]
    ])

    await message.answer(
        "👋 Привет, я Kplay - бот для игр 🎮\n\n"
        "👑 Поддержка:\n"
        "@Kplay_support\n\n"
        "📜 Команды:\n"
        "• Б / баланс — баланс\n"
        "• Бонус — бонус (12ч)\n"
        "• 100 красное / красное 100\n"
        "• 100 черное / черное 100\n"
        "• 100 орел / орел 100\n"
        "• 100 решка / решка 100\n"
        "• Сапер 100\n"
        "• Карты 100\n"
        "• Куб / кубик\n"
        "• Баскетбол / Баскет\n"
        "• Казино, казик, спин, 777, деп, рулетка, крутилка\n"
        "• Топ, балансы\n"
        "• Антоп / бектоп (антоп убирает ссылку на твой профиль из топа)\n"
        "• Промокод / промо (название промокода)\n\n"
        "Канал @kplaynews",
        reply_markup=kb
    )

# ---------- ЛОГ ----------

def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {text}\n")

# ---------- USERS ----------

def add_user(uid):
    uid = str(uid)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(uid + "\n")
        return

    with open(USERS_FILE, "r") as f:
        users = set(x.strip() for x in f if x.strip())

    if uid not in users:
        with open(USERS_FILE, "a") as f:
            f.write(uid + "\n")

def get_all_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return [int(x.strip()) for x in f if x.strip().isdigit()]

#--------------- КД ------------

SPAM_LIMIT = 3        # сообщений
SPAM_INTERVAL = 4    # секунд
SPAM_MUTE = 2        # секунд

user_messages = defaultdict(lambda: deque())
user_muted_until = {}

from aiogram.dispatcher.middlewares.base import BaseMiddleware

class AntiSpamMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not isinstance(event, types.Message):
            return await handler(event, data)

        uid = event.from_user.id
        now = time.time()

        if uid in user_muted_until and user_muted_until[uid] > now:
            return  # ❗ тихо блокируем, но НЕ жрём хендлеры

        q = user_messages[uid]
        while q and now - q[0] > SPAM_INTERVAL:
            q.popleft()

        q.append(now)

        if len(q) >= SPAM_LIMIT:
            user_muted_until[uid] = now + SPAM_MUTE
            q.clear()
            return

        return await handler(event, data)
        
dp.message.middleware(AntiSpamMiddleware())
   
# ---------- БАЛАНС ----------

import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")
conn.commit()


def add_user(user_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()


def get_balance(user_id: int) -> int:
    add_user(user_id)

    cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()

    return result[0] if result else 0


def add_balance(user_id: int, amount: int):
    add_user(user_id)

    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()


@dp.message(lambda m: m.text and m.text.lower() in ["б", "баланс", "/b", "/bal", "/balance", "балик", "бал"])
async def balance_cmd(msg: types.Message):
    user_id = msg.from_user.id
    bal = get_balance(user_id)
    await msg.reply(f"💰 Баланс: {fmt(bal)} {CURRENCY}")
    
# ---------- БОНУС ----------

@dp.message(lambda m: m.text and m.text.lower() in  ["бонус", "/bonus"])
async def bonus(msg: types.Message):
    add_user(msg.from_user.id)
    uid = msg.from_user.id
    now = int(datetime.now().timestamp())

    last = bonus_cd.get(uid, 0)
    if now - last < BONUS_TIME:
        wait = BONUS_TIME - (now - last)
        h = wait // 3600
        m = (wait % 3600) // 60
        await msg.reply(f"⏳ Бонус через {h}ч {m}м")
        return

    bonus_cd[uid] = now
    add_balance(uid, 3000)
    bal = get_balance(uid)
    await msg.reply(f"🎁 +3000 {CURRENCY}")

#-------------------- СМАЙЛЫ ЛУДКИ -----------

@dp.message(lambda m: m.text and m.text.lower() in ["куб", "кубик", "/cube"])
async def dice_game(msg: types.Message):
    await msg.reply_dice(emoji="🎲")
    
@dp.message(lambda m: m.text and m.text.lower() in ["баскет", "баскетбол", "/basket", "/basketball"])
async def basket_game(msg: types.Message):
    await msg.reply_dice(emoji="🏀")


@dp.message(lambda m: m.text and m.text.lower() in [
    "казино", "казик", "спин", "777", "деп", "рулетка", "крутилка", "/spin", "/dep", "/777", "/casino"
])
async def casino_game(msg: types.Message):
    await msg.reply_dice(emoji="🎰")

#-------------- ПРОСТЫЕ ОТВЕТЫ ----------------

@dp.message(lambda m: m.text and m.text.lower() == "пиу")
async def cmd_piu(msg: types.Message):
    await msg.reply("Пау")

@dp.message(lambda m: m.text and m.text.lower() == "пинг")
async def cmd_ping(msg: types.Message):
    await msg.reply("Понг")

@dp.message(lambda m: m.text and m.text.lower() == "до")
async def cmd_do(msg: types.Message):
    await msg.reply("Дооооо")
    
@dp.message(lambda m: m.text and m.text.lower() == "бот")
async def cmd_botik(msg: types.Message):
    await msg.reply("Я тут")

#------------- ПОКУПКА ВАЛЮТЫ -------------

from aiogram.types import LabeledPrice
from aiogram.enums import ChatType

@dp.message(lambda m: m.text and m.text.lower().startswith(("купить", "/buy")))
async def buy_currency(msg: types.Message):

    parts = msg.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        return await msg.reply("❌ Формат: купить 1")

    stars = int(parts[1])

    if stars <= 0:
        return await msg.reply("❌ Минимум 1 ⭐")

    if stars > 10000:
        return await msg.reply("❌ Если сумма больше 10.000 обратитесь в @kplay_support")

    amount_currency = stars * 500

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Купить", callback_data=f"buy_yes:{stars}")
    kb.button(text="❌ Отмена", callback_data="buy_no")
    kb.adjust(2)

    await msg.reply(
        f"💳 Покупка валюты\n\n"
        f"⭐ Звёзды: {stars}\n"
        f"💰 Получите: {amount_currency:,} {CURRENCY}\n"
        f"📈 Курс: 1 ⭐ = 500 {CURRENCY}",
        reply_markup=kb.as_markup()
    )
    
@dp.callback_query(lambda c: c.data.startswith("buy_yes"))
async def buy_confirm(call: types.CallbackQuery):
    stars = int(call.data.split(":")[1])

    await call.message.delete()

    await bot.send_invoice(
        chat_id=call.from_user.id,
        title="💰 Покупка валюты",
        description=f"{stars} ⭐ → {stars * 500} {CURRENCY}",
        payload=f"buy_{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Покупка валюты", amount=stars)],
    )
    
@dp.callback_query(lambda c: c.data == "buy_no")
async def buy_cancel(call: types.CallbackQuery):
    await call.message.edit_text("❌ Покупка отменена")
    
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(lambda m: m.successful_payment)
async def successful_payment(msg: types.Message):
    payload = msg.successful_payment.invoice_payload

    if payload.startswith("buy_"):
        stars = int(payload.split("_")[1])
        currency_amount = stars * 500

        add_balance(msg.from_user.id, currency_amount)

        await msg.answer(
            f"✅ Оплата прошла успешно!\n\n"
            f"💰 Вам начислено: {currency_amount:,} {CURRENCY}\n"
            f"Спасибо за покупку ⭐"
        )

#--------------- ПРОМОКОДЫ -----------

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS promocodes (
    name TEXT PRIMARY KEY,
    amount INTEGER,
    uses_left INTEGER,
    expires_at INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promo_used (
    user_id INTEGER,
    promo_name TEXT,
    PRIMARY KEY (user_id, promo_name)
)
""")

conn.commit()

def create_promo(name, amount, uses):
    conn = sqlite3.connect("database.db") 
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO promocodes 
        (name, amount, uses_left, expires_at)
        VALUES (?, ?, ?, NULL)
    """, (name.lower(), amount, uses))

    conn.commit()
    conn.close()

@dp.message(F.text.startswith("+промо"))
async def add_promo(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split()

    if len(args) != 4:
        await message.answer(
            "❌ Формат:\n"
            "+промо название сумма количество"
        )
        return

    _, name, amount_str, uses_str = args

    # проверка суммы
    try:
        amount = int(amount_str)
    except:
        await message.answer("❌ Сумма должна быть числом")
        return

    # проверка количества
    try:
        uses = int(uses_str)
    except:
        await message.answer("❌ Количество должно быть числом")
        return

    if uses <= 0:
        await message.answer("❌ Количество должно быть больше 0")
        return

    create_promo(name, amount, uses)

    await message.answer(
        f"✅ Промокод {name} создан\n"
        f"💰 Сумма: {amount}\n"
        f"📦 Активаций: {uses}"
    )
        
@dp.message(F.text.startswith("-промо"))
async def delete_promo(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    try:
        _, name = message.text.split()
        name = name.lower()

        cursor.execute("SELECT name FROM promocodes WHERE name=?", (name,))
        promo = cursor.fetchone()

        if not promo:
            await message.answer("❌ Промокод не найден")
            return

        cursor.execute("DELETE FROM promocodes WHERE name=?", (name,))
        conn.commit()

        await message.answer(f"🗑 Промокод {name} удалён")

    except:
        await message.answer("❌ Формат: -промо название")
        
from datetime import datetime

@dp.message(F.text.lower().in_(["промокоды", "промы"]))
async def list_promos(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    cursor.execute("SELECT name, uses_left, expires_at FROM promocodes")
    promos = cursor.fetchall()

    if not promos:
        await message.answer("❌ Промокодов нет")
        return

    text = "📋 Список промокодов:\n\n"

    for name, uses_left, expires_at in promos:
        if uses_left is not None:
            text += f"{name} | {uses_left} активаций\n"
        elif expires_at is not None:
            dt = datetime.fromtimestamp(expires_at)
            formatted = dt.strftime("%d.%m.%Y %H:%M")
            text += f"{name} | {formatted}\n"
        else:
            text += f"{name} | Без ограничений\n"

    await message.answer(text)
        
@dp.message(F.text.lower().startswith(("промо", "промокод")))
async def activate_promo(message: types.Message):
    try:
        parts = message.text.split()
        name = parts[1].lower()
    except:
        await message.answer("❌ Укажите название промокода")
        return

    cursor.execute("SELECT * FROM promocodes WHERE name=?", (name,))
    promo = cursor.fetchone()

    if not promo:
        await message.answer("❌ Промокод не найден")
        return

    name, amount, uses_left, expires_at = promo
    uid = message.from_user.id

    # проверка использовал ли
    cursor.execute("SELECT * FROM promo_used WHERE user_id=? AND promo_name=?", (uid, name))
    if cursor.fetchone():
        await message.answer("❌ Вы уже использовали этот промокод")
        return

    # проверка срока
    if expires_at and int(time.time()) > expires_at:
        await message.answer("❌ Срок действия промокода истек")
        return

    # проверка количества
    if uses_left is not None:
        if uses_left <= 0:
            await message.answer("❌ Лимит активаций исчерпан")
            return

        cursor.execute(
            "UPDATE promocodes SET uses_left = uses_left - 1 WHERE name=?",
            (name,)
        )

    # начисление
    add_balance(uid, amount)

    cursor.execute(
        "INSERT INTO promo_used VALUES (?, ?)",
        (uid, name)
    )

    conn.commit()

    await message.answer(f"🎉 Промокод активирован!\n+{amount} playks")
   
# -------------------- 50/50 -------------------------

@dp.message(
    lambda m: m.text
    and len(m.text.split()) == 2
    and m.text.lower().replace("ё", "е").split()[0] in {
        "орел", "решка", "красное", "черное"
    }
)
async def game_5050(msg: types.Message):
    text = msg.text.lower().replace("ё", "е").split()
    choice, amount = text

    if not amount.isdigit():
        return

    bet = int(amount)

    coin_choices = ["орел", "решка"]
    color_choices = ["красное", "черное"]

    uid = msg.from_user.id
    add_user(uid)

    if get_balance(uid) < bet:
        return await msg.reply("❌ Недостаточно средств")

    # ---------- МОНЕТКА ----------
    if choice in coin_choices:
        add_balance(uid, -bet)
        result = random.choice(coin_choices)

        if choice == result:
            win = bet * 2
            add_balance(uid, win)
            await msg.reply(f"🪙 Выпало: {result}\n🎉 +{fmt(win)} {CURRENCY}")
        else:
            await msg.reply(f"🪙 Выпало: {result}\n💥 Проигрыш")
        return

    # ---------- КРАСНОЕ / ЧЕРНОЕ ----------
    if choice in color_choices:
        add_balance(uid, -bet)
        result = random.choice(color_choices)

        if choice == result:
            win = bet * 2
            add_balance(uid, win)
            await msg.reply(f"🎰 Выпало: {result}\n🎉 +{fmt(win)} {CURRENCY}")
        else:
            await msg.reply(f"🎰 Выпало: {result}\n💥 Проигрыш")
        return
        
# ---------- САПЁР ----------

@dp.message(lambda m: m.text and re.fullmatch(r"(сапер|сапёр)\s+\d+", m.text.lower()))
async def miner(msg: types.Message):
    add_user(msg.from_user.id)
    bet = int(msg.text.split()[1])
    uid = msg.from_user.id

    if get_balance(uid) < bet:
        await msg.reply("❌ Недостаточно средств")
        return

    add_balance(uid, -bet)

    mines = set(random.sample(range(25), 5))
    miners[uid] = {"bet": bet, "mult": 1.0, "mines": mines, "open": set()}

    kb = InlineKeyboardBuilder()
    for i in range(25):
        kb.button(text="⬜", callback_data=f"s_{i}_{uid}")
    kb.button(text="💰 Забрать", callback_data=f"s_cash_{uid}")
    kb.adjust(5)

    await msg.reply(
        f"💣 Сапёр\nСтавка: {bet} {CURRENCY}\nМножитель: 1.0x",
        reply_markup=kb.as_markup()
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("s_"))
async def miner_click(call: types.CallbackQuery):
    await call.answer()

    _, action, owner = call.data.split("_")
    owner = int(owner)

    if call.from_user.id != owner:
        return

    if owner not in miners:
        return

    game = miners[owner]

    if action == "cash":
        win = int(game["bet"] * game["mult"])
        add_balance(owner, win)
        del miners[owner]
        await call.message.edit_text(f"🏆 Ты забрал приз\n+{fmt(win)} {CURRENCY}")
        return

    idx = int(action)

    if idx in game["open"]:
        return

    if idx in game["mines"]:
        del miners[owner]
        await call.message.edit_text("💥 БАХ!")
        return

    game["open"].add(idx)

    # 🎲 Новый баланс множителя
    if random.random() < 0.6:
        game["mult"] += 0.1
    else:
        game["mult"] += 0.2

    kb = InlineKeyboardBuilder()
    for i in range(25):
        if i in game["open"]:
            kb.button(text="🟩", callback_data="x")
        else:
            kb.button(text="⬜", callback_data=f"s_{i}_{owner}")

    kb.button(text="💰 Забрать", callback_data=f"s_cash_{owner}")
    kb.adjust(5)

    await call.message.edit_text(
        f"💣 Сапёр\nМножитель: {game['mult']:.1f}x",
        reply_markup=kb.as_markup()
    )

#--------------- КАРТЫ -----------------

@dp.message(lambda m: m.text and re.fullmatch(r"карты\s+\d+", m.text.lower()))
async def start_card_game(msg: types.Message):
    add_user(msg.from_user.id)

    uid = msg.from_user.id
    bet = int(msg.text.split()[1])

    if get_balance(uid) < bet:
        await msg.reply("❌ Недостаточно средств")
        return

    add_balance(uid, -bet)

    card_games[uid] = {
        "bet": bet,
        "stage": 0,
        "mult": 1.0,
        "history": []
    }

    kb = InlineKeyboardBuilder()
    for i in range(3):
        kb.button(text="🃏", callback_data=f"card_{i}_{uid}")
    kb.button(text="💰 Забрать", callback_data=f"card_cash_{uid}")
    kb.adjust(3,1)

    await msg.reply(
        f"🃏 Партия началась \n"
        f"Раунд: 1/5\n"
        f"Множитель: 1.0x",
        reply_markup=kb.as_markup()
    )
    
@dp.callback_query(lambda c: c.data.startswith("card_"))
async def card_click(call: types.CallbackQuery):
    await call.answer()

    parts = call.data.split("_")

    action = parts[1]
    uid = int(parts[2])

    # 🔒 ЗАЩИТА — ТОЛЬКО ВЛАДЕЛЕЦ ИГРЫ
    if call.from_user.id != uid:
        await call.answer("❌ Это не твоя игра", show_alert=True)
        return

    game = card_games.get(uid)
    if not game:
        return

    # 💰 ЗАБРАТЬ
    if action == "cash":
        win = int(game["bet"] * game["mult"])
        add_balance(uid, win)
        del card_games[uid]       
        await call.message.edit_text(
            f"💰 Ты забрал приз\n"
            f"Выигрыш: {fmt(win)} {CURRENCY}"
        )
        return

    idx = int(parts[1])
    uid = int(parts[2])

    if call.from_user.id != uid:
        return

    game = card_games.get(uid)
    if not game:
        return

    death = random.randint(0, 2)

    row = []
    alive = True
    for i in range(3):
        if i == death:
            row.append("💀")
        else:
            row.append("✅")

    game["history"].append(row)

    if idx == death:
        text = "💥 Проигрыш!\n\n"
        for r in game["history"]:
            text += " ".join(f"[{x}]" for x in r) + "\n"

        await call.message.edit_text(text)
        del card_games[uid]
        return

    # ✅ ПРОШЁЛ
    game["stage"] += 1
    game["mult"] *= 1.2

    if game["stage"] >= 5:
        win = int(game["bet"] * game["mult"])
        add_balance(uid, win)
        await call.message.edit_text(
            f"🏆 5/5\n"
            f"💰 Выигрыш: {win} {CURRENCY}"
        )
        del card_games[uid]
        return

    text = ""
    for r in game["history"]:
        text += " ".join(f"[{x}]" for x in r) + "\n"
    text += "\n" + " ".join("[🃏]" for _ in range(3))

    kb = InlineKeyboardBuilder()
    for i in range(3):
        kb.button(text="🃏", callback_data=f"card_{i}_{uid}")
    kb.button(text="💰 Забрать", callback_data=f"card_cash_{uid}")
    kb.adjust(3,1)

    await call.message.edit_text(
        f"{text}\n\n"
        f"Раунд: {game['stage'] + 1}/5\n"
        f"Множитель: {game['mult']:.2f}x",
        reply_markup=kb.as_markup()
    )

# --------------------- ТОП ------------------------

@dp.message(lambda m: m.text and m.text.lower() in [
    "топ", "/top", "/stat", "балансы", "/baltop"
])
async def show_top(msg: types.Message):
    rows = cur.execute(
    "SELECT user_id, balance FROM balances WHERE user_id NOT IN (?, ?) AND balance > 0 ORDER BY balance DESC LIMIT 10",
    (OWNER_ID, SUPPORT_ID)
).fetchall()

    if not rows:
        return await msg.reply("🏆 Топ пуст")

    hidden = {
        x[0] for x in cur.execute("SELECT user_id FROM untop").fetchall()
    }

    text = "🏆 <b>Топ балансов</b>\n\n"

    for i, (uid, bal) in enumerate(rows, 1):
        bal = fmt(bal)

        if uid in hidden:
            # 👁 скрыт
            line = f"{i}. {uid} [👁] — {bal} {CURRENCY}\n"
        else:
            # 👤 обычный
            line = (
                f'{i}. <a href="tg://openmessage?user_id={uid}">{uid}</a> '
                f"— {bal} {CURRENCY}\n"
            )

        text += line

    await msg.reply(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    
#------- антоп --------

@dp.message(lambda m: m.text and m.text.lower() in ["/untop", "антоп"])
async def untop_cmd(msg: types.Message):
    uid = msg.from_user.id

    cur.execute(
        "INSERT OR IGNORE INTO untop (user_id) VALUES (?)",
        (uid,)
    )
    db.commit()

    await msg.reply("🙈 Ты скрыт в топе\nТвой профиль больше не будет ссылкой")
    
@dp.message(lambda m: m.text and m.text.lower() in ["/backtop", "бектоп"])
async def backtop_cmd(msg: types.Message):
    uid = msg.from_user.id

    cur.execute(
        "DELETE FROM untop WHERE user_id = ?",
        (uid,)
    )
    db.commit()

    await msg.reply("👀 Ты снова отображаешься в топе с ссылкой на профиль")
    
# ---------- ВЫДАТЬ / СНЯТЬ ----------

def user_label(user: types.User):
    return f"@{user.username}" if user.username else str(user.id)

@dp.message(lambda m: m.text and m.text.lower().startswith("выдать"))
async def give(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return

    parts = msg.text.lower().split()

    # ---------- выдать 1000 всем ----------
    if len(parts) == 3 and parts[2] == "всем":
        amount = int(parts[1])
        count = 0

        for uid in get_all_users():
            if uid != msg.from_user.id:
                add_balance(uid, amount)
                count += 1

        await msg.reply(
            f"🛡 Админ KPlay выдал всем юзерам бота {amount} {CURRENCY}\n"
            f"👥 Получили: {count}"
        )
        return

    # ---------- ответом ----------
    if msg.reply_to_message and len(parts) == 2:
        amount = int(parts[1])
        user = msg.reply_to_message.from_user
        add_balance(user.id, amount)
        await msg.reply(
            f"🛡 Админ KPlay выдал {amount} {CURRENCY} {user_label(user)}"
        )
        return

    # ---------- выдать 1000 id ----------
    if len(parts) == 3 and parts[2].isdigit():
        amount = int(parts[1])
        uid = int(parts[2])
        add_balance(uid, amount)
        await msg.reply(
            f"🛡 Админ KPlay выдал {amount} {CURRENCY} {uid}"
        )

@dp.message(lambda m: m.text and m.text.lower().startswith("снять"))
async def take(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return

    parts = msg.text.split()

    if msg.reply_to_message and len(parts) == 2:
        amount = int(parts[1])
        user = msg.reply_to_message.from_user
        add_balance(user.id, -amount)
        await msg.reply(f"🛡 Админ KPlay снял {amount} {CURRENCY} у {user_label(user)}")
        return

    if len(parts) == 3:
        amount = int(parts[1])
        uid = int(parts[2])
        add_balance(uid, -amount)
        await msg.reply(f"🛡 Админ KPlay снял {amount} {CURRENCY} у {uid}")

# ---------- ПЕРЕДАЧА (п 100) ----------

@dp.message()
async def transfer(msg: types.Message):
    if not msg.text:
        return

    text = msg.text.lower().split()

    if text[0] != "отдать":
        return

    if len(text) < 2 or not text[1].isdigit():
        await msg.reply("❌ Пример: Отдать 10000 (ответом на сообщение)")
        return

    if not msg.reply_to_message:
        await msg.reply("❌ Используй команду ответом на сообщение")
        return

    sender = msg.from_user
    receiver = msg.reply_to_message.from_user
    if receiver.id == OWNER_ID:
        return await msg.reply("❌ Админу переводить нельзя")
    amount = int(text[1])

    if receiver.is_bot:
        await msg.reply("❌ Боту нельзя передавать валюту")
        return

    if sender.id == receiver.id:
        await msg.reply("❌ Нельзя передать самому себе")
        return

    if amount <= 0:
        await msg.reply("❌ Сумма должна быть больше 0")
        return

    if get_balance(sender.id) < amount:
        await msg.reply("❌ Недостаточно средств")
        return

    # 🔹 МАЛАЯ СУММА — БЕЗ ПОДТВЕРЖДЕНИЯ
    if amount < 10_000:
        add_balance(sender.id, -amount)
        add_balance(receiver.id, amount)

        await msg.reply(
            f"💸 {user_label(sender)} передал {fmt(amount)} {CURRENCY} {user_label(receiver)}"
        )
        return

    # 🔹 ПОДТВЕРЖДЕНИЕ
    tid = f"{sender.id}:{receiver.id}:{amount}"

    pending_transfers[tid] = {
        "from": sender.id,
        "to": receiver.id,
        "amount": amount
    }

    from_name = f"@{sender.username}" if sender.username else f"ID {sender.id}"
    to_name = f"@{receiver.username}" if receiver.username else f"ID {receiver.id}"

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"pay_yes:{tid}")
    kb.button(text="❌ Отмена", callback_data=f"pay_no:{tid}")
    kb.adjust(2)

    await msg.reply(
        f"⚠️ *Подтверждение операции*\n\n"
        f"💸 Сумма: `{fmt(amount)}`\n"
        f"👤 Отправитель: {from_name}\n"
        f"🎯 Получатель: {to_name}\n\n"
        f"Вы уверены?",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    
@dp.callback_query(lambda c: c.data.startswith("pay_yes:"))
async def confirm_pay(call: types.CallbackQuery):
    tid = call.data.split(":", 1)[1]

    data = pending_transfers.get(tid)
    if not data:
        await call.answer("❌ Операция не найдена", show_alert=True)
        return

    if call.from_user.id != data["from"]:
        await call.answer("❌ Это не ваша операция", show_alert=True)
        return

    if get_balance(data["from"]) < data["amount"]:
        await call.message.edit_text("❌ Недостаточно средств")
        pending_transfers.pop(tid, None)
        return

    add_balance(data["from"], -data["amount"])
    add_balance(data["to"], data["amount"])

    pending_transfers.pop(tid, None)

    await call.message.edit_text(
        f"✅ Перевод выполнен\n"
        f"💸 {fmt(data['amount'])}"
    )

    await call.answer()
    
@dp.callback_query(lambda c: c.data.startswith("pay_no:"))
async def cancel_pay(call: types.CallbackQuery):
    tid = call.data.split(":", 1)[1]

    data = pending_transfers.get(tid)
    if not data:
        await call.answer("❌ Уже отменено", show_alert=True)
        return

    if call.from_user.id != data["from"]:
        await call.answer("❌ Это не ваша операция", show_alert=True)
        return

    pending_transfers.pop(tid, None)

    await call.message.edit_text("❌ Перевод отменён")
    await call.answer()
    
#--------------- ФИКС "алала 7" ------------

import re
from aiogram import types

# все игровые команды, которые принимают ставку
GAME_COMMANDS = {
    "карты",
    "сапер",
    "красное",
    "черное",
    "орел",
    "решка"
}

def parse_bet(text: str):
    if not text:
        return None, None

    text = text.lower().replace("ё", "е").strip()

    for cmd in GAME_COMMANDS:
        m = re.fullmatch(rf"{cmd}\s+(\d+)", text)
        if m:
            return cmd, int(m.group(1))

    return None, None


@dp.message()
async def universal_games(msg: types.Message):
    cmd, bet = parse_bet(msg.text)

    if not cmd:
        return  # ❗ НЕ ИГРА — НЕ ЛОМАЕМ ДРУГИЕ КОМАНДЫ

    if bet <= 0:
        return await msg.reply("❌ Ставка должна быть больше 0")

    # ⬇️ РАСКИДЫВАЙ ПО СВОИМ ФУНКЦИЯМ
    if cmd == "карты":
        await play_cards(msg, bet)

    elif cmd == "сапер":
        await play_mines(msg, bet)

    elif cmd in ("красное", "черное", "орел", "решка"):
        await play_roulette(msg, cmd, bet)

# ---------- ЗАПУСК ----------

from aiohttp import web
import asyncio
from aiogram.types import ReplyKeyboardRemove

async def handle(request):
    return web.Response(text="ВСЕ РАБОТАЕТ")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

async def main():
    log("Bot started")
    await start_web()
    await dp.start_polling(bot)

if __name__ == "__main__":
 asyncio.run(main())
