import asyncio
import random
import os
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 5338814259

BALANCE_FILE = "balances.txt"
LOG_FILE = "logs.txt"
USERS_FILE = "users.txt"

BONUS_TIME = 12 * 60 * 60
CURRENCY = "playks"

bonus_cd = {}

bot = Bot(TOKEN)
dp = Dispatcher()

balances = {}
miners = {}

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

def load_balances():
    data = {}
    if not os.path.exists(BALANCE_FILE):
        return data

    with open(BALANCE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if ":" not in line:
                continue
            uid, bal = line.strip().split(":", 1)
            if uid.isdigit() and bal.lstrip("-").isdigit():
                data[int(uid)] = int(bal)
    return data

def save_balances():
    with open(BALANCE_FILE, "w", encoding="utf-8") as f:
        for uid, bal in balances.items():
            f.write(f"{uid}:{bal}\n")

balances = load_balances()

def get_balance(uid):
    return balances.get(uid, 0)

def add_balance(uid, amount):
    balances[uid] = get_balance(uid) + amount
    save_balances()

# ---------- БАЛАНС ----------

@dp.message(lambda m: m.text and m.text.lower() in ["б", "баланс"])
async def balance(msg: types.Message):
    add_user(msg.from_user.id)
    await msg.reply(f"💰 Баланс: {get_balance(msg.from_user.id)} {CURRENCY}")

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

# ---------- КРАСНОЕ / ЧЁРНОЕ ----------

@dp.message(lambda m: m.text and re.fullmatch(
    r"(\d+\s+(красное|черное|чёрное|red|black))|((красное|черное|чёрное|red|black)\s+\d+)",
    m.text.lower()
))
async def roulette(msg: types.Message):
    add_user(msg.from_user.id)

    parts = msg.text.lower().split()

    if parts[0].isdigit():
        bet = int(parts[0])
        color_raw = parts[1]
    else:
        color_raw = parts[0]
        bet = int(parts[1])

    color = "red" if color_raw in ["красное", "red"] else "black"
    uid = msg.from_user.id

    if get_balance(uid) < bet:
        await msg.reply("❌ Недостаточно средств")
        return

    add_balance(uid, -bet)
    win_color = random.choice(["red", "black"])

    if color == win_color:
        win = bet * 2
        add_balance(uid, win)
        await msg.reply(
            f"🎉 Победа!\n+{win} {CURRENCY}\n💰 Баланс: {get_balance(uid)} {CURRENCY}"
        )
    else:
        await msg.reply(
            f"💥 Проигрыш\n💰 Баланс: {get_balance(uid)} {CURRENCY}"
        )

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
    kb.adjust(5)
    kb.button(text="💰 ", callback_data=f"s_cash_{uid}")

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
    kb.adjust(5)
    kb.button(text="💰 ", callback_data=f"s_cash_{owner}")

    await call.message.edit_text(
        f"💣 Сапёр\nМножитель: {game['mult']:.1f}x",
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
        "👑 Мои админы:\n"+
        "владелец: @qua4t\n\n"+
        "📜 Команды:\n"+
        "• Б / баланс — баланс\n"+
        "• Бонус — бонус (12ч)\n"+
        "• 100 красное / красное 100\n"+
        "• 100 черное / черное 100\n"+
        "• Сапер 100\n\n"+
        "Канал @kplaynews",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# ---------- ПЕРЕДАЧА (п 100) ----------

@dp.message(lambda m: m.text and re.fullmatch(r"п\s+\d+", m.text.lower()))
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

# ---------- ЗАПУСК ----------

async def main():
    log("Bot started")
    await dp.start_polling(bot)

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
