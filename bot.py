import os
import asyncio
import requests
import random
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")
DA_URL = os.getenv("DA_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== БАЗА =====
conn = sqlite3.connect("vpn.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")

conn.commit()

pending_codes = {}
processed_ids = set()


# ===== МЕНЮ =====
def menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Пополнить")
    kb.add("👤 Профиль")
    return kb


# ===== ПОЛУЧИТЬ БАЛАНС =====
def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()

    if result:
        return result[0]
    else:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return 0


# ===== ДОБАВИТЬ ДЕНЬГИ =====
def add_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()


# ===== СТАРТ =====
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    get_balance(msg.from_user.id)

    await msg.answer(
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать в Moonlight VPN!\n\n"
        "⚡ Быстрый и стабильный VPN для ваших устройств.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Техническая Поддержка — @mtfunit\n\n"
        "👇 Выберите действие:",
        reply_markup=menu()
    )


# ===== ПРОФИЛЬ =====
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(msg: types.Message):
    bal = get_balance(msg.from_user.id)

    await msg.answer(
        f"👤 Профиль\n\n"
        f"Баланс: {bal}₽\n"
        f"ID: {msg.from_user.id}\n"
        f"Тариф: ❌ Нет активной подписки"
    )


# ===== ПОПОЛНЕНИЕ =====
@dp.message_handler(lambda m: m.text == "💰 Пополнить")
async def deposit(msg: types.Message):
    code = str(random.randint(100000, 999999))
    pending_codes[code] = msg.from_user.id

    await msg.answer(
        f"💳 Пополнение\n\n"
        f"1. Перейди по ссылке:\n{DA_URL}\n\n"
        f"2. В комментарии укажи код:\n"
        f"👉 {code}\n\n"
        f"3. Введи любую сумму\n\n"
        f"💸 Деньги придут автоматически"
    )


# ===== ПРОВЕРКА ДОНАТОВ =====
async def check_donations():
    while True:
        try:
            headers = {
                "Authorization": f"Bearer {DA_TOKEN}"
            }

            r = requests.get(
                "https://www.donationalerts.com/api/v1/alerts/donations",
                headers=headers
            )

            data = r.json()

            if "data" in data:
                for d in data["data"]:
                    donate_id = d["id"]

                    if donate_id in processed_ids:
                        continue

                    processed_ids.add(donate_id)

                    amount = int(float(d["amount"]))
                    message = d.get("message", "")

                    for code, user_id in list(pending_codes.items()):
                        if code in message:
                            add_balance(user_id, amount)

                            await bot.send_message(
                                user_id,
                                f"💰 Баланс пополнен на {amount}₽"
                            )

                            del pending_codes[code]
                            break

        except Exception as e:
            print("Ошибка:", e)

        await asyncio.sleep(5)


# ===== ЗАПУСК =====
async def main():
    asyncio.create_task(check_donations())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
