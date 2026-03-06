# -*- coding: utf-8 -*-
import asyncio
import sqlite3
import random
import os
import re

OWNER_ID = 5338814259

def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")

db = sqlite3.connect("balances.db", check_same_thread=False)
cur = db.cursor()

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

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")
db.commit()

cur.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    user_id INTEGER,
    item TEXT,
    amount INTEGER,
    PRIMARY KEY (user_id, item)
)
""")
db.commit()


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
    add_user_file(uid)

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
                url="https://t.me/kplaybase/26",
            )
        ]
    ])
        
    await message.answer(
    "Установка меню",
    reply_markup=main_menu()
)

    await message.answer(
        '<tg-emoji emoji-id="5251694694525586163">✋</tg-emoji> Привет, я Kplay - бот для игр\n\n'
        '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> Поддержка:\n'
        "@Kplay_support\n\n"
        '<tg-emoji emoji-id="5197269100878907942">✍️</tg-emoji> Команды:\n'
        "• Б / баланс\n"
        "• Бонус (12ч)\n"
        "• 100 красное / красное 100\n"
        "• 100 черное / черное 100\n"
        "• 100 орел / орел 100\n"
        "• 100 решка / решка 100\n"
        "• Сапер 100\n"
        "• Карты 100\n"
        "• Куб / кубик\n"
        "• Баскетбол / Баскет\n"
        "• Казино, казик, спин, 777, деп, рулетка, крутилка\n"
        "• Топ / балансы\n"
        "• Антоп / бектоп (антоп убирает ссылку на твой профиль из топа)\n"
        "• Купить (сумма сколько хотите потратить звезд на покупку валюты)\n"
        "• Промокод / промо (название промокода)\n"
        "• Факт / интересное\n"
        "• Скажи (текст)\n"
        "• -Соо, -смс, удалить (ответом на соо которое хотите удалить)\n\n"
        '<tg-emoji emoji-id="5244837092042750681">📈</tg-emoji> Курс: 1 <tg-emoji emoji-id="5438496463044752972">⭐️</tg-emoji> = 1000 playks\n\n'
        '<tg-emoji emoji-id="5305699699204837855">🍀</tg-emoji> Удачной игры!',
        reply_markup=kb,
        parse_mode="HTML")

# ---------- ЛОГ ----------

def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {text}\n")

# ---------- USERS ----------

def add_user_file(uid):
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

SPAM_LIMIT = 10        # сообщений
SPAM_INTERVAL = 10    # секунд
SPAM_MUTE = 10        # секунд

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
            return

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

def add_user(user_id: int):

    cur.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )

    db.commit()

def get_balance(user_id: int) -> int:
    add_user(user_id)

    cur.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cur.fetchone()

    return result[0] if result else 0


def add_balance(user_id: int, amount: int):
    add_user(user_id)

    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id)
    )
    db.commit()


@dp.message(lambda m: m.text and m.text.lower() in ["б", "баланс", "/b", "/balance", "балик",])
async def balance_cmd(msg: types.Message):
    user_id = msg.from_user.id
    bal = get_balance(user_id)
    await msg.reply(f'<tg-emoji emoji-id="5287231198098117669">💰</tg-emoji> Баланс: {fmt(bal)} {CURRENCY}',
        parse_mode="HTML")
    
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
        await msg.reply(f'<tg-emoji emoji-id="5382194935057372936">⏱</tg-emoji> Бонус через {h}ч {m}м',
        parse_mode="HTML")
        return

    bonus_cd[uid] = now
    add_balance(uid, 3000)
    bal = get_balance(uid)
    await msg.reply(f'<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> +3000 {CURRENCY}',
        parse_mode="HTML")

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
    
@dp.message(lambda m: m.text and m.text.lower() == "бот")
async def cmd_botik(msg: types.Message):
    await msg.reply('Я тут <tg-emoji emoji-id="5206607081334906820">✔️</tg-emoji>',
    parse_mode="HTML")
    
@dp.message(lambda m: m.text and m.text.lower() == "поддержка")
async def support_handler(msg: types.Message):
    """Работает с любым регистром"""
    await msg.reply(
        '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> По вопросам писать @kplay_support',
        parse_mode="HTML")
    
#------------- ПОКУПКА ВАЛЮТЫ -------------

from aiogram.types import LabeledPrice
from aiogram.enums import ChatType

@dp.message(lambda m: m.text and m.text.lower().startswith(("купить", "/buy")))
async def buy_currency(msg: types.Message):

    parts = msg.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        return await msg.reply(f'<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Формат: купить 1',
        parse_mode="HTML")

    stars = int(parts[1])

    if stars <= 0:
        return await msg.reply(f'<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Минимум 1 <tg-emoji emoji-id="5438496463044752972">⭐️</tg-emoji>',
        parse_mode="HTML")

    if stars > 20000:
        return await msg.reply(f'<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Если сумма больше 20.000 обратитесь в @kplay_support',
        parse_mode="HTML")

    amount_currency = stars * 1000

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Купить", callback_data=f"buy_yes:{stars}")
    kb.button(text="❌ Отмена", callback_data="buy_no")
    kb.adjust(2)

    await msg.reply(
        f'<tg-emoji emoji-id="5402186569006210455">💱</tg-emoji> Покупка валюты\n\n'
        f'<tg-emoji emoji-id="5438496463044752972">⭐️</tg-emoji> Звёзды: {stars}\n'
        f'<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> Получите: {amount_currency:,} {CURRENCY}\n'
        f'<tg-emoji emoji-id="5244837092042750681">📈</tg-emoji> Курс: 1 <tg-emoji emoji-id="5438496463044752972">⭐️</tg-emoji> = 1000 {CURRENCY}',
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    
@dp.callback_query(lambda c: c.data.startswith("buy_yes"))
async def buy_confirm(call: types.CallbackQuery):
    stars = int(call.data.split(":")[1])

    await call.message.delete()

    await bot.send_invoice(
        chat_id=call.from_user.id,
        title="💰 Покупка валюты",
        description=f"{stars} ⭐ → {stars * 1000} {CURRENCY}",
        payload=f"buy_{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Покупка валюты", amount=stars)],
    )
    
@dp.callback_query(lambda c: c.data == "buy_no")
async def buy_cancel(call: types.CallbackQuery):
    await call.message.edit_text('<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Покупка отменена',
    parse_mode="HTML")
    
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(lambda m: m.successful_payment)
async def successful_payment(msg: types.Message):
    payload = msg.successful_payment.invoice_payload

    if payload.startswith("buy_"):
        stars = int(payload.split("_")[1])
        currency_amount = stars * 1000

        add_balance(msg.from_user.id, currency_amount)

        await msg.answer(
            f'<tg-emoji emoji-id="5278745506657370417">🎉</tg-emoji> Оплата прошла успешно!\n\n'
            f'<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> Вам начислено: {currency_amount:,} {CURRENCY}\n'
            f"Спасибо за покупку!",
            parse_mode="HTML")

#--------------- ПРОМОКОДЫ -----------

cur.execute("""
CREATE TABLE IF NOT EXISTS promocodes (
    name TEXT PRIMARY KEY,
    amount INTEGER,
    uses_left INTEGER,
    expires_at INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS promo_used (
    user_id INTEGER,
    promo_name TEXT,
    PRIMARY KEY (user_id, promo_name)
)
""")
db.commit()

def create_promo(name, amount, uses):

    cur.execute("""
        INSERT OR REPLACE INTO promocodes 
        (name, amount, uses_left, expires_at)
        VALUES (?, ?, ?, NULL)
    """, (name.lower(), amount, uses))
    db.commit()

@dp.message(F.text.startswith("+промо"))
async def add_promo(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split()

    if len(args) != 4:
        await message.reply(
            "❌ Формат:\n"
            "+промо название сумма количество"
        )
        return

    _, name, amount_str, uses_str = args

    # проверка суммы
    try:
        amount = int(amount_str)
    except:
        await message.reply("❌ Сумма должна быть числом")
        return

    # проверка количества
    try:
        uses = int(uses_str)
    except:
        await message.reply("❌ Количество должно быть числом")
        return

    if uses <= 0:
        await message.reply("❌ Количество должно быть больше 0")
        return

    create_promo(name, amount, uses)

    await message.reply(
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

        cur.execute("SELECT name FROM promocodes WHERE name=?", (name,))
        promo = cur.fetchone()

        if not promo:
            await message.reply("❌ Промокод не найден")
            return

        # удаляем промокод
        cur.execute("DELETE FROM promocodes WHERE name=?", (name,))

        # очищаем использование
        cur.execute("DELETE FROM promo_used WHERE promo_name=?", (name,))

        db.commit()

        await message.reply(f"🗑 Промокод {name} удалён")

    except:
        await message.reply("❌ Формат: -промо название")

@dp.message(F.text.lower().in_(["промокоды", "промы"]))
async def list_promos(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    cur.execute("SELECT name, amount, uses_left, expires_at FROM promocodes")
    promos = cur.fetchall()

    if not promos:
        await message.reply("❌ Промокодов нет")
        return

    text = "📋 Список промокодов:\n\n"

    for name, amount, uses_left, expires_at in promos:
        # Если есть лимит использований
        if uses_left is not None:
            text += f"{name} | {amount} {CURRENCY} | {uses_left} активаций\n"
        # Если есть дата окончания
        elif expires_at is not None:
            dt = datetime.fromtimestamp(expires_at)
            formatted = dt.strftime("%d.%m.%Y %H:%M")
            text += f"{name} | даёт: {amount} | истекает: {formatted}\n"
        # Без ограничений
        else:
            text += f"{name} | {amount} {CURRENCY} | Без ограничений\n"

    await message.reply(text)
        
@dp.message(F.text.lower().startswith(("промо", "промокод")))
async def activate_promo(message: types.Message):

    try:
        parts = message.text.split()
        name = parts[1].lower()
    except:
        await message.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Укажите название промокода',
        parse_mode="HTML")
        return

    cur.execute("SELECT * FROM promocodes WHERE name=?", (name,))
    promo = cur.fetchone()

    if not promo:
        await message.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Промокод не найден',
        parse_mode="HTML")
        return

    name, amount, uses_left, expires_at = promo
    uid = message.from_user.id

    # проверка количества
    if uses_left is not None:
        if uses_left <= 0:
            await message.reply(
            '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Лимит активаций исчерпан',
            parse_mode="HTML")
            return

    # проверка использовал ли
    cur.execute(
        "SELECT * FROM promo_used WHERE user_id=? AND promo_name=?",
        (uid, name)
    )

    if cur.fetchone():
        await message.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Вы уже использовали этот промокод',
        parse_mode="HTML")
        return

    # списываем активацию
    if uses_left is not None:
        cur.execute(
            "UPDATE promocodes SET uses_left = uses_left - 1 WHERE name=?",
            (name,)
        )

    add_balance(uid, amount)

    cur.execute(
        "INSERT INTO promo_used VALUES (?, ?)",
        (uid, name)
    )

    db.commit()

    await message.reply(
    f'<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> Промокод активирован!\n+{amount} playks',
    parse_mode="HTML")
   
#--------------- ФАКТЫ --------------

import random
from aiogram import F, types

facts = [
    "У осьминогов три сердца.",
    "Бананы это ягоды, а клубника нет.",
    "Мёд никогда не портится.",
    "Акулы существуют дольше, чем деревья.",
    "В космосе нет звука.",
    "Сердце синего кита весит около 180 кг.",
    "Пчёлы могут распознавать лица.",
    "Самая короткая война длилась менее часа.",
    "Человеческий мозг вырабатывает электричество.",
    "У коал отпечатки пальцев похожи на человеческие.",
    "Солнце составляет 99,8% массы Солнечной системы.",
    "В Венере сутки длиннее года.",
    "Крокодилы не могут высовывать язык.",
    "Кошки могут издавать более 100 разных звуков.",
    "Осьминоги могут менять цвет за секунды.",
    "Дельфины называют друг друга по именам.",
    "Молния горячее поверхности Солнца.",
    "У человека около 37 триллионов клеток.",
    "Летучие мыши единственные летающие млекопитающие.",
    "Улитки могут спать до трёх лет.",
    "Вода может кипеть и замерзать одновременно.",
    "У жирафа столько же шейных позвонков, сколько у человека.",
    "Луна удаляется от Земли примерно на 3-4 см в год.",
    "Пингвины делают предложения, даря камешки.",
    "Сахара когда-то была зелёной.",
    "У медуз нет мозга.",
    "Муравьи могут поднимать вес в 50 раз больше своего.",
    "Лошади могут спать стоя.",
    "ДНК человека и банана совпадает примерно на 60%.",
    "Сердце человека бьётся более 100 000 раз в день.",
    "На Марсе закаты голубые.",
    "Океаны покрывают более 70% поверхности Земли.",
    "В теле человека 206 костей.",
    "Страусы могут бежать до 70 км/ч.",
    "У акул нет костей, только хрящи.",
    "Земля не идеально круглая.",
    "Самый большой живой организм - гриб в США.",
    "В организме человека больше бактерий, чем клеток.",
    "Человеческий нос может запомнить тысячи запахов.",
    "Некоторые черепахи могут дышать через клоаку.",
    "Самая длинная молния была более 700 км.",
    "В Мировом океане исследовано меньше 10%.",
    "В космосе есть облака из спирта.",
    "У совы глаза не вращаются.",
    "Киты могут общаться на огромных расстояниях.",
    "В радуге нет отдельного фиолетового слоя, это смесь цветов.",
    "На Юпитере возможны алмазные дожди (по теории).",
    "Самая высокая гора от основания - Мауна-Кеа.",
    "Гора Эверест растёт каждый год.",
    "В космосе есть планеты со стеклянным дождём.",
    "Человек светится в темноте, но слишком слабо, чтобы это увидеть.",
    "Самая высокая зафиксированная температура на Земле - выше 56°C.",
    "В мире больше деревьев, чем звёзд в Млечном Пути (оценочно).",
    "В космосе существуют гигантские водные резервуары.",
    "Акулы чувствуют электрические поля.",
    "Осьминоги обладают высоким интеллектом.",
    "Некоторые виды бамбука растут до метра в день.",
    "У коров есть лучшие друзья.",
    "Лимоны содержат больше сахара, чем клубника.",
    "Планета Уран вращается на боку."
]

@dp.message(F.text.lower().in_(["факт", "интересное"]))
async def random_fact(message: types.Message):
    fact = random.choice(facts)
    await message.reply(f'<tg-emoji emoji-id="5436113877181941026">❓</tg-emoji> Интересный факт\n\n{fact}',
    parse_mode="HTML")
  
#---------------- СКАЖИ -----------------

from aiogram import types

@dp.message(F.text.lower().startswith("скажи "))
async def say_command(message: types.Message):
    text = message.text[6:]  # убираем "скажи "

    if not text.strip():
        await message.reply("Скажи, что именно нужно сказать?")
        return

    # Формируем сообщение с упоминанием юзера
    username = message.from_user.username
    if username:
        reply_text = f"@{username} попросил сказать:\n{text}"
    else:
        # если юзера нет юзернейма, используем имя
        reply_text = f"{message.from_user.full_name} попросил сказать:\n{text}"

    await message.reply(reply_text)

#------------- МОДЕРАЦИЯ -----------

#----- удаление соо -----

@dp.message(lambda m: m.text and m.text.lower() in ["удалить", "-соо", "-смс", "/delete", "/del", "delete"])
async def admin_delete(msg: types.Message):

    # только в группах
    if msg.chat.type not in ["group", "supergroup"]:
        return

    # только ответом
    if not msg.reply_to_message:
        return

    try:
        # проверяем админ ли
        member = await bot.get_chat_member(
            msg.chat.id,
            msg.from_user.id
        )

        if member.status not in ["administrator", "creator"]:
            return

        # удаляем сообщение на которое ответили
        await bot.delete_message(
            msg.chat.id,
            msg.reply_to_message.message_id
        )

        # удаляем саму команду
        await bot.delete_message(
            msg.chat.id,
            msg.message_id
        )

    except Exception as e:
        print("delete error:", e)
        
# -------- ОБНУЛЕНИЕ --------

@dp.message(lambda m: m.text and m.text.lower() in ["обнуление","/wipe"])
async def wipe_balances(msg: types.Message):

    if msg.from_user.id != OWNER_ID:
        return

    cur.execute(
    "UPDATE users SET balance = 0 WHERE user_id NOT IN (?, ?)",
    (OWNER_ID, SUPPORT_ID)
)

    await msg.reply(
        "Все балансы обнулены."
    )
    
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
        return await msg.reply('<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Недостаточно средств',
        parse_mode="HTML")

    # ---------- МОНЕТКА ----------
    if choice in coin_choices:
        add_balance(uid, -bet)
        result = random.choice(coin_choices)

        if choice == result:
            win = bet * 2
            add_balance(uid, win)
            await msg.reply(f'<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji> Выпало: {result}\n<tg-emoji emoji-id="5278745506657370417">🎉</tg-emoji> +{fmt(win)} {CURRENCY}',
            parse_mode="HTML")
        else:
            await msg.reply(f'<tg-emoji emoji-id="5199552030615558774">🪙</tg-emoji> Выпало: {result}\n<tg-emoji emoji-id="5276032951342088188">💥</tg-emoji> Проигрыш',
            parse_mode="HTML")
        return

    # ---------- КРАСНОЕ / ЧЕРНОЕ ----------
    if choice in color_choices:
        add_balance(uid, -bet)
        result = random.choice(color_choices)

        if choice == result:
            win = bet * 2
            add_balance(uid, win)
            await msg.reply(f'<tg-emoji emoji-id="5305699699204837855">🍀</tg-emoji> Выпало: {result}\n<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> +{fmt(win)} {CURRENCY}',
            parse_mode="HTML")
        else:
            await msg.reply(f'<tg-emoji emoji-id="5305699699204837855">🍀</tg-emoji> Выпало: {result}\n<tg-emoji emoji-id="5276032951342088188">💥</tg-emoji> Проигрыш',
            parse_mode="HTML")
        return
        
# ---------- САПЁР ----------

@dp.message(lambda m: m.text and re.fullmatch(r"(сапер|сапёр)\s+\d+", m.text.lower()))
async def miner(msg: types.Message):
    add_user(msg.from_user.id)

    uid = msg.from_user.id
    bet = int(msg.text.split()[1])

    if get_balance(uid) < bet:
        await msg.reply(
            '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Недостаточно средств',
            parse_mode="HTML"
        )
        return

    add_balance(uid, -bet)

    mines = set(random.sample(range(25), 5))

    miners[uid] = {
        "bet": bet,
        "mult": 1.0,
        "mines": mines,
        "open": set(),
        "locked": False,
        "clicked": False
    }

    kb = InlineKeyboardBuilder()

    for i in range(25):
        kb.button(text="❓", callback_data=f"s_{i}_{uid}")

    kb.button(text="❌", callback_data="ignore")
    kb.adjust(5)

    await msg.reply(
        f'<tg-emoji emoji-id="5386514237638067415">💣</tg-emoji> Сапёр\n'
        f"Множитель: 1.0x\n"
        f"{fmt(bet)} {CURRENCY}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


# ===== ФИНАЛЬНОЕ ПОЛЕ =====
def build_final_field(game):
    kb = InlineKeyboardBuilder()

    for i in range(25):
        # показываем мины
        if i in game["mines"]:
            kb.button(text="💣", callback_data="ignore")
        # всё остальное прозрачное
        else:
            kb.button(text=" ", callback_data="ignore")

    kb.adjust(5)
    return kb


# ===== НАЖАТИЕ =====
@dp.callback_query(lambda c: c.data and c.data.startswith("s_"))
async def miner_click(call: types.CallbackQuery):
    parts = call.data.split("_")
    action = parts[1]
    owner = int(parts[2])

    if call.from_user.id != owner:
        return

    game = miners.get(owner)
    if not game:
        return

    if game["locked"]:
        return

    game["locked"] = True
    await call.answer()

    # ===== ЗАБРАТЬ =====
    if action == "cash":
        if not game["clicked"]:
            game["locked"] = False
            return

        win = int(game["bet"] * game["mult"])
        add_balance(owner, win)

        kb = build_final_field(game)
        del miners[owner]

        await call.message.edit_text(
            f'<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> Ты забрал приз\n'
            f"+{fmt(win)} {CURRENCY}",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
        return

    idx = int(action)

    # ===== МИНА =====
    if idx in game["mines"]:
        kb = build_final_field(game)
        del miners[owner]

        await call.message.edit_text(
            '<tg-emoji emoji-id="5276032951342088188">💥</tg-emoji> БАХ!',
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
        return

    # ===== УГАДАЛ =====
    game["open"].add(idx)
    game["clicked"] = True

    if random.random() < 0.5:
        game["mult"] += 0.1
    else:
        game["mult"] += 0.2

    win = int(game["bet"] * game["mult"])

    kb = InlineKeyboardBuilder()
    for i in range(25):
        if i in game["open"]:
            kb.button(text=" ", callback_data="ignore")
        else:
            kb.button(text="❓", callback_data=f"s_{i}_{owner}")

    if game["clicked"]:
        kb.button(text="💰 Забрать", callback_data=f"s_cash_{owner}")
    else:
        kb.button(text="❌", callback_data="ignore")

    kb.adjust(5)

    await call.message.edit_text(
        f'<tg-emoji emoji-id="5469913852462242978">🧨</tg-emoji> Сапёр\n'
        f"Множитель: {game['mult']:.1f}x\n"
        f"{fmt(win)} {CURRENCY}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

    game["locked"] = False


#--------------- КАРТЫ -----------------
@dp.message(lambda m: m.text and re.fullmatch(r"карты\s+\d+", m.text.lower()))
async def start_card_game(msg: types.Message):
    add_user(msg.from_user.id)

    uid = msg.from_user.id
    bet = int(msg.text.split()[1])

    if get_balance(uid) < bet:
        await msg.reply(
            '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Недостаточно средств',
            parse_mode="HTML"
        )
        return

    add_balance(uid, -bet)

    card_games[uid] = {
        "bet": bet,
        "stage": 0,
        "mult": 1.0,
        "rows": [],
        "locked": False,
        "clicked": False
    }

    kb = InlineKeyboardBuilder()
    for i in range(3):
        kb.button(text="🃏", callback_data=f"card_{i}_{uid}")

    kb.button(text="❌", callback_data="ignore")
    kb.adjust(3, 1)

    current_win = int(bet * 1.0)

    await msg.reply(
        f'<tg-emoji emoji-id="5386514237638067415">🃏</tg-emoji> Партия началась\n'
        f"Раунд: 1/5\n"
        f"Множитель: 1.00x\n"
        f"{fmt(current_win)} {CURRENCY}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


# ===== нажатие =====
@dp.callback_query(lambda c: c.data.startswith("card_"))
async def card_click(call: types.CallbackQuery):
    parts = call.data.split("_")
    action = parts[1]
    uid = int(parts[2])

    if call.from_user.id != uid:
        return

    game = card_games.get(uid)
    if not game:
        return

    if game["locked"]:
        return

    game["locked"] = True
    await call.answer()

    # ===== ЗАБРАТЬ =====
    if action == "cash":
        if not game["clicked"]:
            game["locked"] = False
            return

        win = int(game["bet"] * game["mult"])
        add_balance(uid, win)

        kb = InlineKeyboardBuilder()
        for r in game["rows"]:
            for x in r:
                kb.button(text=x if x == "💀" else " ", callback_data="ignore")
        kb.adjust(3)

        await call.message.edit_text(
            f'<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> Ты забрал приз\n'
            f"{fmt(win)} {CURRENCY}",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )

        del card_games[uid]
        return

    # ===== выбор =====
    idx = int(parts[1])
    death = random.randint(0, 2)
    row = []

    for i in range(3):
        if i == death:
            row.append("💀")
        else:
            row.append("✅")

    game["rows"].append(row)
    game["clicked"] = True

    # ===== ПРОИГРАЛ =====
    if idx == death:
        kb = InlineKeyboardBuilder()
        for r in game["rows"]:
            for x in r:
                kb.button(text=x if x == "💀" else " ", callback_data="ignore")
        kb.adjust(3)

        await call.message.edit_text(
            '<tg-emoji emoji-id="5276032951342088188">💥</tg-emoji> Проигрыш!',
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )

        del card_games[uid]
        return

    # ===== ПРОШЁЛ =====
    game["stage"] += 1
    game["mult"] *= 1.2

    # ===== ПОБЕДА =====
    if game["stage"] >= 5:
        win = int(game["bet"] * game["mult"])
        add_balance(uid, win)

        kb = InlineKeyboardBuilder()
        for r in game["rows"]:
            for x in r:
                kb.button(text=x if x == "💀" else " ", callback_data="ignore")
        kb.adjust(3)

        await call.message.edit_text(
            f'<tg-emoji emoji-id="5278745506657370417">🎉</tg-emoji> 5/5\n'
            f'<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> {fmt(win)} {CURRENCY}',
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )

        del card_games[uid]
        return

    # ===== продолжаем =====
    kb = InlineKeyboardBuilder()
    # старые ряды
    for r in game["rows"]:
        for x in r:
            kb.button(text=x, callback_data="ignore")
    # новый ряд
    for i in range(3):
        kb.button(text="🃏", callback_data=f"card_{i}_{uid}")

    if game["clicked"]:
        kb.button(text="💰 Забрать", callback_data=f"card_cash_{uid}")
    else:
        kb.button(text="❌", callback_data="ignore")

    kb.adjust(3, 3, 3, 3, 3, 1)

    win_now = int(game["bet"] * game["mult"])

    await call.message.edit_text(
        f"Раунд: {game['stage']+1}/5\n"
        f"Множитель: {game['mult']:.2f}x\n"
        f"{fmt(win_now)} {CURRENCY}",
        reply_markup=kb.as_markup()
    )

    game["locked"] = False

# --------------------- ТОП ------------------------

@dp.message(lambda m: m.text and m.text.lower() in [
    "топ", "/top", "/stat", "балансы", "/baltop"
])
async def show_top(msg: types.Message):

    rows = cur.execute(
        "SELECT user_id, balance FROM users "
        "WHERE user_id NOT IN (?, ?) AND balance > 0 "
        "ORDER BY balance DESC LIMIT 10",
        (OWNER_ID, SUPPORT_ID)
    ).fetchall()

    if not rows:
        return await msg.reply('<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> Топ пуст',
        parse_mode="HTML")

    hidden = {
        x[0] for x in cur.execute(
            "SELECT user_id FROM untop"
        ).fetchall()
    }

    text = '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> <b>Топ балансов</b>\n\n'
    parse_mode="HTML"

    for i, (uid, bal) in enumerate(rows, 1):

        bal = fmt(bal)

        # получаем имя
        try:
            user = await msg.bot.get_chat(uid)
            name = user.full_name or str(uid)
        except:
            name = str(uid)

        if uid in hidden:
            line = f'{i}. {name} [<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji>] — {bal} {CURRENCY}\n'
            parse_mode="HTML"
        else:
            line = (
                f'{i}. <a href="tg://openmessage?user_id={uid}">{name}</a> '
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

    await msg.reply('<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji> Ты скрыт в топе\nТвой профиль больше не будет ссылкой',
    parse_mode="HTML")
    
@dp.message(lambda m: m.text and m.text.lower() in ["/backtop", "бектоп"])
async def backtop_cmd(msg: types.Message):
    uid = msg.from_user.id

    cur.execute(
        "DELETE FROM untop WHERE user_id = ?",
        (uid,)
    )
    db.commit()

    await msg.reply('<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji> Ты снова отображаешься в топе с ссылкой на профиль',
    parse_mode="HTML")
    
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

# ---------- ПЕРЕДАЧА ----------

@dp.message()
async def transfer(msg: types.Message):

    if not msg.text:
        return

    text = msg.text.lower().split()

    if not text:
        return

# ---------- ОТДАТЬ ОТВЕТОМ ----------

    if text[0] != "отдать":
        return

    if len(text) < 2 or not text[1].isdigit():

        await msg.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Пример: Отдать 10000 (ответом на сообщение)',
        parse_mode="HTML")
        return


    if not msg.reply_to_message:

        await msg.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Используй команду ответом на сообщение',
        parse_mode="HTML")
        return


    sender = msg.from_user
    receiver = msg.reply_to_message.from_user

    if receiver.id == OWNER_ID:
        return await msg.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Админу переводить нельзя',
        parse_mode="HTML")

    amount = int(text[1])

    if receiver.is_bot:

        await msg.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Боту нельзя передавать валюту',
        parse_mode="HTML")
        return


    if sender.id == receiver.id:

        await msg.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Нельзя передать самому себе',
        parse_mode="HTML")
        return


    if amount <= 0:

        await msg.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Сумма должна быть больше 0',
        parse_mode="HTML")
        return


    if get_balance(sender.id) < amount:

        await msg.reply(
        '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji> Недостаточно средств',
        parse_mode="HTML")
        return


# 🔹 маленький перевод

    if amount < 10_000:

        add_balance(sender.id,-amount)
        add_balance(receiver.id,amount)

        await msg.reply(
            f'<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji> {user_label(sender)} передал {fmt(amount)} {CURRENCY} {user_label(receiver)}',
            parse_mode="HTML"
        )

        return


# ---------- ПОДТВЕРЖДЕНИЕ ----------

    tid=f"{sender.id}:{receiver.id}:{amount}"

    pending_transfers[tid]={

        "from":sender.id,
        "to":receiver.id,
        "amount":amount,
        "time": time.time()

    }

    from_name=f"@{sender.username}" if sender.username else f"ID {sender.id}"
    to_name=f"@{receiver.username}" if receiver.username else f"ID {receiver.id}"

    kb=InlineKeyboardBuilder()

    kb.button(text="✅ Подтвердить",callback_data=f"pay_yes:{tid}")
    kb.button(text="❌ Отмена",callback_data=f"pay_no:{tid}")

    kb.adjust(2)

    await msg.reply(

        f'<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> Подтверждение операции\n\n'
        f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> Сумма: {fmt(amount)}\n'
        f'<tg-emoji emoji-id="5201691993775818138">🛫</tg-emoji> Отправитель: {from_name}\n'
        f'<tg-emoji emoji-id="5310278924616356636">🎯</tg-emoji> Получатель: {to_name}\n\n'
        f"Вы уверены?",

        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    
#--------------- ФИКС "алала 7" ------------

import re

GAME_COMMANDS = {
    "карты",
    "сапер",
    "сапёр",
    "красное",
    "черное",
    "орел",
    "решка"
}

def parse_bet(text: str):
    if not text:
        return None, None

    text = text.lower().replace("ё", "е").strip()

    m = re.fullmatch(
        r"(карты|сапер|сапёр|красное|черное|орел|решка)\s+(\d+)",
        text
    )

    if not m:
        return None, None

    return m.group(1), int(m.group(2))


@dp.message()
async def universal_games(msg: types.Message):

    cmd, bet = parse_bet(msg.text)

    if not cmd:
        return

    if bet <= 0:
        return await msg.reply("❌ Ставка должна быть больше 0")

    # 🔥 ПРОСТО ПЕРЕДАЕМ СООБЩЕНИЕ В УЖЕ ГОТОВЫЕ ХЕНДЛЕРЫ

    if cmd in ("карты",):
        await start_card_game(msg)

    elif cmd in ("сапер", "сапёр"):
        await miner(msg)

    elif cmd in ("красное", "черное", "орел", "решка"):
        await game_5050(msg)

# ---------- КНОПКИ ЛС ----------

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu():

    return ReplyKeyboardMarkup(

        keyboard=[

            [
                KeyboardButton(text="Баланс"),
                KeyboardButton(text="Бонус")
            ],

            [
                KeyboardButton(text="Топ"),
                KeyboardButton(text="Антоп"),
                KeyboardButton(text="Бектоп"),
            ],

            [
                KeyboardButton(text="Поддержка"),
                KeyboardButton(text="/start") 
            ]

        ],

        resize_keyboard=True
    )

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
