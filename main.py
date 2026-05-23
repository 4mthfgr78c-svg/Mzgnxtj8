import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from config import BOT_TOKEN, ADMIN_IDS
from data import CATEGORIES, CITY_NAME
from keyboards import city_keyboard, main_menu, subcategories_menu, items_list, location_phone_keyboard

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Файл для хранения user_id всех пользователей
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_users(users_set):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users_set), f)

users = load_users()

def add_user(user_id):
    if user_id not in users:
        users.add(user_id)
        save_users(users)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    add_user(user_id)
    await message.answer(
        f"🧘 Добро пожаловать в КЫОР. Велнес Гид по {CITY_NAME}!\n\n"
        "Я бесплатный справочник: сауны, СПА, кемпинги, здоровье, спорт, образование.\n"
        "📍 У каждого места есть адрес и телефон.\n\n"
        "Выберите город:",
        reply_markup=city_keyboard()
    )

@dp.callback_query(F.data == "city_select")
async def city_selected(call: CallbackQuery):
    await call.message.edit_text(
        f"Главное меню • {CITY_NAME}",
        reply_markup=main_menu()
    )
    await call.answer()

@dp.callback_query(F.data == "main_menu")
async def back_to_main(call: CallbackQuery):
    await call.message.edit_text(
        f"Главное меню • {CITY_NAME}",
        reply_markup=main_menu()
    )
    await call.answer()

@dp.callback_query(F.data.startswith("cat_"))
async def show_subcategories(call: CallbackQuery):
    cat_key = call.data.split("_")[1]
    cat_name = CATEGORIES[cat_key]["name"]
    await call.message.edit_text(
        f"{CATEGORIES[cat_key]['icon']} {cat_name}\nВыберите раздел:",
        reply_markup=subcategories_menu(cat_key)
    )
    await call.answer()

@dp.callback_query(F.data.startswith("back_sub_"))
async def back_to_subcat(call: CallbackQuery):
    cat_key = call.data.split("_")[2]
    await show_subcategories(call)  # переиспользуем

@dp.callback_query(F.data.startswith("sub_"))
async def show_items(call: CallbackQuery):
    _, cat_key, sub_key = call.data.split("_")
    items = CATEGORIES[cat_key]["subcats"][sub_key]["items"]
    if not items:
        await call.answer("Нет заведений", show_alert=True)
        return
    # Сохраняем в callback_data текущую страницу? Начнём с 0
    await call.message.edit_text(
        f"📍 {CATEGORIES[cat_key]['subcats'][sub_key]['name']}\nВыберите заведение:",
        reply_markup=items_list(cat_key, sub_key, items, page=0)
    )
    await call.answer()

@dp.callback_query(F.data.startswith("nav_"))
async def paginate_items(call: CallbackQuery):
    _, cat_key, sub_key, page_str = call.data.split("_")
    page = int(page_str)
    items = CATEGORIES[cat_key]["subcats"][sub_key]["items"]
    await call.message.edit_reply_markup(reply_markup=items_list(cat_key, sub_key, items, page=page))
    await call.answer()

@dp.callback_query(F.data.startswith("item_"))
async def show_item_card(call: CallbackQuery):
    _, cat_key, sub_key, idx_str = call.data.split("_")
    idx = int(idx_str)
    items = CATEGORIES[cat_key]["subcats"][sub_key]["items"]
    if idx >= len(items):
        await call.answer("Ошибка", show_alert=True)
        return
    item = items[idx]
    text = f"🏷 *{item['name']}*\n"
    if item.get("description"):
        text += f"📖 {item['description']}\n"
    text += f"📍 *Адрес:* {item['address']}\n"
    if item.get("phone"):
        text += f"📞 *Телефон:* `{item['phone']}`"
    else:
        text += f"📞 Телефон не указан"
    
    await call.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=location_phone_keyboard(
            item['address'], 
            item.get('phone', ''),
            item.get('lat'), 
            item.get('lon')
        )
    )
    await call.answer()

@dp.callback_query(F.data == "back_to_items")
async def back_to_items_list(call: CallbackQuery):
    # Нужно восстановить предыдущее состояние: категория, подкатегория, страница
    # Упрощённо: вернём в главное меню, но это неудобно. Лучше сохранять историю.
    # Для минимализма – просто вернём в главное.
    await call.message.edit_text(
        f"Главное меню • {CITY_NAME}",
        reply_markup=main_menu()
    )
    await call.answer()

# Команда рассылки (только для админов)
@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён.")
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Напишите текст рассылки после команды, например:\n/broadcast Скидка 10% на массаж до пятницы")
        return
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid, f"📢 *Новость от КЫОР*\n\n{text}", parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)  # чтобы не превысить лимиты
        except:
            pass
    await message.answer(f"✅ Рассылка отправлена {sent} пользователям.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())