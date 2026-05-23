import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command
from aiogram.fsm import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from data import PLACES
from keyboards import *
from db import add_user, get_all_users, get_forum, create_topic, add_post

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---- состояния FSM для создания темы и ответа ----
class ForumStates(StatesGroup):
    waiting_title = State()
    waiting_first_post = State()
    waiting_reply = State()

class SearchState(StatesGroup):
    waiting_keyword = State()

# ---- команда старт ----
@dp.message(Command("start"))
async def start_cmd(message: Message):
    add_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    await message.answer(
        "<b>КЬЮР. ВЕЛНЕС ГИД ПО ЮЖНО-САХАЛИНСКУ</b>\n\n"
        "СПРАВОЧНИК МЕСТ, ФОРУМ, ПОИСК.\n"
        "НИКАКОЙ РЕКЛАМЫ — ТОЛЬКО ФАКТЫ И КОНТАКТЫ.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# ---- главное меню и навигация ----
@dp.callback_query(F.data == "main_menu")
async def main_menu_cb(call: CallbackQuery):
    await call.message.edit_text(
        "<b>КЬЮР. ГЛАВНОЕ МЕНЮ</b>",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data == "menu_places")
async def menu_places(call: CallbackQuery):
    await call.message.edit_text(
        "<b>КАТЕГОРИИ МЕСТ</b>",
        reply_markup=places_categories(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data == "places_back")
async def places_back(call: CallbackQuery):
    await menu_places(call)

@dp.callback_query(F.data.startswith("cat_"))
async def show_places_list(call: CallbackQuery):
    cat_key = call.data.split("_")[1]
    items = PLACES.get(cat_key, {}).get("items", [])
    if not items:
        await call.answer("В ЭТОЙ КАТЕГОРИИ ПОКА НЕТ МЕСТ", show_alert=True)
        return
    # сохраняем категорию в данных колбэка (используем message.reply_markup)
    await call.message.edit_text(
        f"<b>{PLACES[cat_key]['name']}</b>\nВЫБЕРИТЕ МЕСТО:",
        reply_markup=places_list(cat_key, items, 0),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data.startswith("page_"))
async def paginate_places(call: CallbackQuery):
    _, cat_key, page_str = call.data.split("_")
    page = int(page_str)
    items = PLACES.get(cat_key, {}).get("items", [])
    await call.message.edit_reply_markup(reply_markup=places_list(cat_key, items, page))
    await call.answer()

@dp.callback_query(F.data.startswith("place_"))
async def show_place(call: CallbackQuery):
    _, cat_key, idx_str = call.data.split("_")
    idx = int(idx_str)
    items = PLACES.get(cat_key, {}).get("items", [])
    if idx >= len(items):
        await call.answer("МЕСТО НЕ НАЙДЕНО", show_alert=True)
        return
    p = items[idx]
    # отправляем альбом фото
    if p.get("photos"):
        media = [InputMediaPhoto(pid) for pid in p["photos"]]
        await call.message.answer_media_group(media=media)
    # текст карточки
    text = f"<b>{p['name']}</b>\n"
    if p.get("desc"):
        text += f"<blockquote>{p['desc']}</blockquote>\n"
    if p.get("address"):
        text += f"📍 {p['address']}\n"
    if p.get("hours"):
        text += f"🕒 {p['hours']}\n"
    if p.get("price"):
        text += f"💰 {p['price']}\n"
    # отправляем карточку и запоминаем, что сейчас в этом месте
    await call.message.answer(
        text,
        reply_markup=place_card_buttons(p.get("phone",""), p.get("lat"), p.get("lon")),
        parse_mode="HTML"
    )
    # сохраняем в данные, чтобы "НАЗАД К СПИСКУ" работало
    await call.answer()

@dp.callback_query(F.data == "back_to_list")
async def back_to_list(call: CallbackQuery):
    # предыдущее сообщение было карточкой, удалим его и вернём список?
    # проще: отправить новое сообщение со списком, а старое оставить
    await call.answer()
    # но лучше вынести: мы не знаем категорию. Пока просто возвращаем в категории
    await menu_places(call)

# ---- ФОРУМ ----
@dp.callback_query(F.data == "menu_forum")
async def forum_menu_cb(call: CallbackQuery):
    await call.message.edit_text(
        "<b>ФОРУМ КЬЮР</b>\nОБЩАЙТЕСЬ, ЗАДАВАЙТЕ ВОПРОСЫ, ДЕЛИТЕСЬ ОПЫТОМ.",
        reply_markup=forum_menu(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data == "forum_list")
async def list_topics(call: CallbackQuery):
    forum = get_forum()
    if not forum:
        await call.message.edit_text(
            "ТЕМ ПОКА НЕТ. БУДЬТЕ ПЕРВЫМ!",
            reply_markup=back_button("menu_forum"),
            parse_mode="HTML"
        )
        await call.answer()
        return
    await call.message.edit_text(
        "<b>СПИСОК ТЕМ</b>",
        reply_markup=topics_list(forum, 0),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data.startswith("forum_page_"))
async def paginate_topics(call: CallbackQuery):
    page = int(call.data.split("_")[2])
    forum = get_forum()
    await call.message.edit_reply_markup(reply_markup=topics_list(forum, page))
    await call.answer()

@dp.callback_query(F.data.startswith("topic_"))
async def view_topic(call: CallbackQuery):
    topic_id = call.data.split("_")[1]
    forum = get_forum()
    topic = forum.get(topic_id)
    if not topic:
        await call.answer("ТЕМА УДАЛЕНА", show_alert=True)
        return
    text = f"<b>{topic['title']}</b>\n\n"
    for post in topic["posts"]:
        name = post["username"] or f"user_{post['user_id']}"
        text += f"<b>{name}</b> [{time.strftime('%d.%m %H:%M', time.localtime(post['time']))}]:\n{post['text']}\n\n"
    if len(text) > 4000:
        text = text[:4000] + "..."
    await call.message.edit_text(
        text,
        reply_markup=topic_controls(topic_id),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data == "forum_create")
async def create_topic_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ForumStates.waiting_title)
    await call.message.answer(
        "ВВЕДИТЕ НАЗВАНИЕ ТЕМЫ (НЕ БОЛЕЕ 100 СИМВОЛОВ):",
        reply_markup=back_button("menu_forum")
    )
    await call.answer()

@dp.message(ForumStates.waiting_title)
async def get_topic_title(message: Message, state: FSMContext):
    if len(message.text) > 100:
        await message.answer("НАЗВАНИЕ СЛИШКОМ ДЛИННОЕ. ПОПРОБУЙТЕ ЕЩЁ (ДО 100):")
        return
    await state.update_data(title=message.text)
    await state.set_state(ForumStates.waiting_first_post)
    await message.answer("ТЕПЕРЬ НАПИШИТЕ ПЕРВОЕ СООБЩЕНИЕ (ТЕКСТ ТЕМЫ):")

@dp.message(ForumStates.waiting_first_post)
async def get_first_post(message: Message, state: FSMContext):
    data = await state.get_data()
    title = data["title"]
    first_post = message.text
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    topic_id = create_topic(user_id, username, title, first_post)
    await state.clear()
    await message.answer(
        f"ТЕМА СОЗДАНА! ID: {topic_id}\nВернуться к форуму?",
        reply_markup=forum_menu()
    )

@dp.callback_query(F.data.startswith("reply_"))
async def start_reply(call: CallbackQuery, state: FSMContext):
    topic_id = call.data.split("_")[1]
    await state.update_data(topic_id=topic_id)
    await state.set_state(ForumStates.waiting_reply)
    await call.message.answer(
        "ВВЕДИТЕ ТЕКСТ ОТВЕТА:",
        reply_markup=back_button("forum_list")
    )
    await call.answer()

@dp.message(ForumStates.waiting_reply)
async def send_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    topic_id = data["topic_id"]
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    ok = add_post(topic_id, user_id, username, message.text)
    await state.clear()
    if ok:
        await message.answer("ОТВЕТ ДОБАВЛЕН.", reply_markup=forum_menu())
        # показать тему
        forum = get_forum()
        topic = forum[topic_id]
        text = f"<b>{topic['title']}</b>\n\n"
        for post in topic["posts"]:
            name = post["username"] or f"user_{post['user_id']}"
            text += f"<b>{name}</b> [{time.strftime('%d.%m %H:%M', time.localtime(post['time']))}]:\n{post['text']}\n\n"
        await message.answer(text[:4000], reply_markup=topic_controls(topic_id), parse_mode="HTML")
    else:
        await message.answer("ОШИБКА. ТЕМА НЕ НАЙДЕНА.", reply_markup=forum_menu())

# ---- ПОИСК ПО МЕСТАМ ----
@dp.callback_query(F.data == "menu_search")
async def search_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_keyword)
    await call.message.answer(
        "ВВЕДИТЕ КЛЮЧЕВОЕ СЛОВО ДЛЯ ПОИСКА ПО МЕСТАМ:",
        reply_markup=back_button("main_menu")
    )
    await call.answer()

@dp.message(SearchState.waiting_keyword)
async def do_search(message: Message, state: FSMContext):
    keyword = message.text.lower().strip()
    results = []
    for cat_key, cat in PLACES.items():
        for idx, p in enumerate(cat["items"]):
            if keyword in p["name"].lower() or keyword in p.get("desc", "").lower():
                results.append((cat_key, idx, p["name"]))
    if not results:
        await message.answer("НИЧЕГО НЕ НАЙДЕНО.")
        await state.clear()
        return
    text = "<b>РЕЗУЛЬТАТЫ ПОИСКА:</b>\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat_key, idx, name in results[:10]:
        text += f"• {name}\n"
        kb.inline_keyboard.append([InlineKeyboardButton(text=name, callback_data=f"place_{cat_key}_{idx}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.clear()

# ---- РАССЫЛКА (только админ) ----
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("НЕТ ДОСТУПА")
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("ФОРМАТ: /broadcast ТЕКСТ")
        return
    users = get_all_users()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(int(uid), f"<b>РАССЫЛКА КЬЮР</b>\n\n{text}", parse_mode="HTML")
            sent += 1
        except:
            pass
    await message.answer(f"ОТПРАВЛЕНО {sent} ПОЛЬЗОВАТЕЛЯМ")

# ---- ЗАПУСК ----
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import time
    asyncio.run(main())