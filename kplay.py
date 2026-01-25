# -*- coding: utf-8 -*-
import asyncio
import sqlite3
import random
import os
import re

db = sqlite3.connect("balances.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS balances (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER NOT NULL
)
""")
db.commit()	

from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

TOKEN = "8536913712:AAHh-kgezThCdjQyyA7viMwOn7Q0rFVmcZQ"
OWNER_ID = 5338814259

LOG_FILE = "logs.txt"
USERS_FILE = "users.txt"

BONUS_TIME = 12 * 60 * 60
CURRENCY = "playks"

bonus_cd = {}

bot = Bot(TOKEN)
dp = Dispatcher()

miners = {}
card_games = {}

#---------- ШАБЛОН СТАРТА ----------

@dp.message(lambda m: m.text == "/start")
async def start(msg: types.Message):
    add_user(msg.from_user.id)

    kb = InlineKeyboardBuilder()
    kb.button(
        text="➕ Добавить в чат",
        url=f"https://t.me/{(await bot.me()).username}?startgroup=true"
    )

    await msg.answer(
        "👋 Привет, я Kplay. бот для игр 🎮\n\n"+
        "👑 Поддержка:\n"+
        "@qua4t\n\n"+
        "📜 Команды:\n"+
        "• Б / баланс — баланс\n"+
        "• Бонус — бонус (12ч)\n"+
        "• 100 красное / красное 100\n"+
        "• 100 черное / черное 100\n"+
        "• Сапер 100\n"+
        "• Карты 100\n\n"+
        "Канал @kplaynews",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
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

# ---------- БАЛАНС ----------

@dp.message(lambda m: m.text and m.text.lower() in ["б", "баланс"])
async def balance(msg: types.Message):
    uid = msg.from_user.id
    add_user(uid)
    bal = get_balance(uid)
    await msg.reply(f"💰 Баланс: {bal} {CURRENCY}")

def get_balance(uid: int) -> int:
    cur.execute("SELECT balance FROM balances WHERE user_id=?", (uid,))
    row = cur.fetchone()
    return row[0] if row else 0


def add_balance(uid: int, amount: int):
    cur.execute("""
    INSERT INTO balances (user_id, balance)
    VALUES (?, ?)
    ON CONFLICT(user_id)
    DO UPDATE SET balance = balance + ?
    """, (uid, amount, amount))
    db.commit()
    
# ---------- БОНУС ----------

@dp.message(lambda m: m.text and m.text.lower() == "бонус")
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
    await msg.reply(f"🎁 +3000 {CURRENCY}")

# -------------------- 50/50 -------------------------
@dp.message(
    lambda m: m.text
    and len(m.text.split()) == 2
    and not m.text.lower().startswith((
        "сапер",
        "сапёр",
        "карты",
        "панель",
        "админ",
        "/",
        "бонус",
        "баланс",
        "профиль"
    ))
)
async def universal_bet(msg: types.Message):
    text = msg.text.lower().replace("ё", "е").split()

    bet = None
    choice = None

    for x in text:
        if x.isdigit():
            bet = int(x)
        else:
            choice = x

    if bet is None or choice is None:
        return
async def universal_bet(msg: types.Message):
    text = msg.text.lower().replace("ё", "е").split()

    if len(text) != 2:
        return

    bet = None
    choice = None

    for x in text:
        if x.isdigit():
            bet = int(x)
        else:
            choice = x

    if bet is None or choice is None:
        return

    # допустимые ставки
    coin_choices = ["орел", "решка"]
    color_choices = ["красное", "черное"]

    uid = msg.from_user.id
    add_user(uid)

    if get_balance(uid) < bet:
        return await msg.reply("❌ Недостаточно средств")

    # ---------------- МОНЕТКА ----------------
    if choice in coin_choices:
        add_balance(uid, -bet)
        result = random.choice(coin_choices)

        if choice == result:
            win = bet * 2
            add_balance(uid, win)
            await msg.reply(
                f"🪙 50/50\n"
                f"Выпало: {result}\n"
                f"🎉 Победа! +{win} {CURRENCY}\n"
                f"💰 Баланс: {get_balance(uid)}"
            )
        else:
            await msg.reply(
                f"🪙 50/50\n"
                f"Выпало: {result}\n"
                f"💥 Проигрыш\n"
                f"💰 Баланс: {get_balance(uid)}"
            )
        return

    # ---------------- КРАСНОЕ / ЧЕРНОЕ ----------------
    if choice in color_choices:
        add_balance(uid, -bet)
        result = random.choice(color_choices)

        if choice == result:
            win = bet * 2
            add_balance(uid, win)
            await msg.reply(
                f"🎰 50/50\n"
                f"Выпало: {result}\n"
                f"🎉 Победа! +{win} {CURRENCY}\n"
                f"💰 Баланс: {get_balance(uid)}"
            )
        else:
            await msg.reply(
                f"🎰 50/50\n"
                f"Выпало: {result}\n"
                f"💥 Проигрыш\n"
                f"💰 Баланс: {get_balance(uid)}"
            )
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
        await call.message.edit_text(f"🏆 Забрал приз\n+{win} {CURRENCY}")
        return

    idx = int(action)
    
    # защита от двойного клика
    if idx in game["open"]:
        return
    
    if idx in game["mines"]:
        del miners[owner]
        await call.message.edit_text("💥 БАХ!")
        return

    game["open"].add(idx)
    game["mult"] += 0.2

    kb = InlineKeyboardBuilder()
    for i in range(25):
        if i in game["open"]:
            kb.button(text="🟩", callback_data="x")
        else:
            kb.button(text="⬜", callback_data=f"s_{i}_{owner}")
    kb.button(text="💰 Забрать", callback_data=f"s_cash_{owner}")
    kb.adjust(5, 1)

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

    # 💰 ЗАБРАТЬ
    if parts[1] == "cash":
        uid = int(parts[2])
        game = card_games.get(uid)
        if not game:
            return

        win = int(game["bet"] * game["mult"])
        add_balance(uid, win)
        del card_games[uid]

        await call.message.edit_text(
            f"💰 Ты забрал\n"
            f"Выигрыш: {win} {CURRENCY}"
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

@dp.message(lambda m: m.text and re.fullmatch(r"отдать\s+\d+", m.text.lower()))
async def transfer(msg: types.Message):
    add_user(msg.from_user.id)

    if not msg.reply_to_message:
        await msg.reply("❌ Используй команду ответом на сообщение")
        return

    sender = msg.from_user
    receiver = msg.reply_to_message.from_user

    if sender.id == receiver.id:
        await msg.reply("❌ Нельзя передать самому себе")
        return

    amount = int(msg.text.split()[1])

    if amount <= 0:
        await msg.reply("❌ Сумма должна быть больше 0")
        return

    if get_balance(sender.id) < amount:
        await msg.reply("❌ Недостаточно средств")
        return

    add_balance(sender.id, -amount)
    add_balance(receiver.id, amount)

    await msg.reply(
        f"💸 {user_label(sender)} передал {amount} {CURRENCY} {user_label(receiver)}"
    )
    
# ================== ADMIN PANEL FIXED ==================

ADMIN_LOGIN_CMD = "adminkentkplaytokenpydroid"
ADMIN_PASSWORD = "63580"

BANS_USERS_FILE = "bans_users.txt"
BANS_GROUPS_FILE = "bans_groups.txt"

for f in [BANS_USERS_FILE, BANS_GROUPS_FILE]:
    if not os.path.exists(f):
        open(f, "w").close()

admin_state = {}

# ---------- KEYBOARDS ----------

def main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🚫 Баны", callback_data="adm_bans")
    kb.button(text="💸 Выдать", callback_data="adm_give")
    kb.button(text="➖ Снять", callback_data="adm_take")
    kb.button(text="💰 Балансы", callback_data="adm_bal")
    kb.adjust(2)
    return kb.as_markup()

def back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="← Назад", callback_data="adm_back")
    return kb.as_markup()

# ---------- LOGIN ----------

@dp.message(lambda m: m.text == ADMIN_LOGIN_CMD)
async def admin_login(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return
    admin_state[msg.from_user.id] = {"step": "password"}
    await msg.reply("🔐 Пароль?")

@dp.message(lambda m: admin_state.get(m.from_user.id, {}).get("step") == "password")
async def admin_password(msg: types.Message):
    if msg.text != ADMIN_PASSWORD:
        return await msg.reply("❌ Неверный пароль")
    admin_state[msg.from_user.id] = {}
    await msg.reply("🛡 Админ-панель", reply_markup=main_kb())

# ---------- BACK ----------

@dp.callback_query(lambda c: c.data == "adm_back")
async def adm_back(call: types.CallbackQuery):
    admin_state.pop(call.from_user.id, None)
    await call.message.edit_text("🛡 Админ-панель", reply_markup=main_kb())

# ---------- GIVE ----------

@dp.callback_query(lambda c: c.data == "adm_give")
async def adm_give(call: types.CallbackQuery):
    admin_state[call.from_user.id] = {"step": "give_id"}
    await call.message.edit_text("🆔 Айди?", reply_markup=back_kb())

@dp.message(lambda m: admin_state.get(m.from_user.id, {}).get("step") == "give_id")
async def give_id(msg: types.Message):
    if not msg.text.isdigit():
        return await msg.reply("❌ Айди числом")
    admin_state[msg.from_user.id] = {"step": "give_sum", "uid": int(msg.text)}
    await msg.reply("💰 Сумма?")

@dp.message(lambda m: admin_state.get(m.from_user.id, {}).get("step") == "give_sum")
async def give_sum(msg: types.Message):
    if not msg.text.isdigit():
        return await msg.reply("❌ Число")
    uid = admin_state[msg.from_user.id]["uid"]
    add_balance(uid, int(msg.text))
    admin_state[msg.from_user.id] = {}
    await msg.reply("✅ Успешно", reply_markup=main_kb())

# ---------- TAKE ----------

@dp.callback_query(lambda c: c.data == "adm_take")
async def adm_take(call: types.CallbackQuery):
    admin_state[call.from_user.id] = {"step": "take_id"}
    await call.message.edit_text("🆔 Айди?", reply_markup=back_kb())

@dp.message(lambda m: admin_state.get(m.from_user.id, {}).get("step") == "take_id")
async def take_id(msg: types.Message):
    if not msg.text.isdigit():
        return
    admin_state[msg.from_user.id] = {"step": "take_sum", "uid": int(msg.text)}
    await msg.reply("💰 Сумма?")

@dp.message(lambda m: admin_state.get(m.from_user.id, {}).get("step") == "take_sum")
async def take_sum(msg: types.Message):
    if not msg.text.isdigit():
        return
    uid = admin_state[msg.from_user.id]["uid"]
    add_balance(uid, -int(msg.text))
    admin_state[msg.from_user.id] = {}
    await msg.reply("✅ Успешно", reply_markup=main_kb())

# ---------- BALANCES ----------

@dp.callback_query(lambda c: c.data == "adm_bal")
async def adm_bal(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Проверить баланс", callback_data="bal_check")
    kb.button(text="🏆 Топ", callback_data="bal_top")
    kb.button(text="← Назад", callback_data="adm_back")
    kb.adjust(1)
    await call.message.edit_text("💰 Балансы", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data == "bal_check")
async def bal_check(call: types.CallbackQuery):
    admin_state[call.from_user.id] = {"step": "bal_id"}
    await call.message.edit_text("🆔 Айди?", reply_markup=back_kb())

@dp.message(lambda m: admin_state.get(m.from_user.id, {}).get("step") == "bal_id")
async def bal_id(msg: types.Message):
    if not msg.text.isdigit():
        return
    uid = int(msg.text)
    bal = get_balance(uid)
    admin_state[msg.from_user.id] = {}
    await msg.reply(f"👤 {uid}\n💰 {bal} {CURRENCY}", reply_markup=main_kb())

@dp.callback_query(lambda c: c.data == "bal_top")
async def bal_top(call: types.CallbackQuery):
    cur.execute(
        "SELECT user_id, balance FROM balances WHERE user_id != ? ORDER BY balance DESC LIMIT 10",
        (OWNER_ID,)
    )
    rows = cur.fetchall()

    if not rows:
        return await call.message.edit_text("🏆 Топ пуст", reply_markup=back_kb())

    text = "🏆 Топ:\n"
    for i, (uid, bal) in enumerate(rows, 1):
        text += f"{i}. {uid} — {bal}\n"

    await call.message.edit_text(text, reply_markup=back_kb())

# ---------- BANS ----------

@dp.callback_query(lambda c: c.data == "adm_bans")
async def adm_bans(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Забанить юзера", callback_data="ban_user")
    kb.button(text="📄 Банлист", callback_data="ban_list")
    kb.button(text="← Назад", callback_data="adm_back")
    kb.adjust(1)
    await call.message.edit_text("🚫 Баны", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data == "ban_user")
async def ban_user(call: types.CallbackQuery):
    admin_state[call.from_user.id] = {"step": "ban_uid"}
    await call.message.edit_text("🆔 Айди юзера?", reply_markup=back_kb())

@dp.message(lambda m: admin_state.get(m.from_user.id, {}).get("step") == "ban_uid")
async def ban_uid(msg: types.Message):
    if not msg.text.isdigit():
        return
    with open(BANS_USERS_FILE, "a") as f:
        f.write(msg.text + "\n")
    admin_state[msg.from_user.id] = {}
    await msg.reply("🚫 Забанен", reply_markup=main_kb())

@dp.callback_query(lambda c: c.data == "ban_list")
async def ban_list(call: types.CallbackQuery):
    with open(BANS_USERS_FILE) as f:
        data = f.read().strip()
    await call.message.edit_text("📄 Банлист:\n" + (data or "пусто"), reply_markup=back_kb())

# ---------- ЗАПУСК ----------

from aiohttp import web
import asyncio

async def handle(request):
    return web.Response(text="Kplay bot is alive!")

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
