import asyncio
import json
import os
import time
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from data import PLACES

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ----- JSON ХРАНИЛИЩА -----
USERS_FILE = "users.json"
FORUM_FILE = "forum.json"

def _load(f):
    if not os.path.exists(f):
        return {}
    with open(f, "r", encoding="utf-8") as file:
        return json.load(file)

def _save(f, data):
    with open(f, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

def add_user(user_id, username):
    users = _load(USERS_FILE)
    if str(user_id) not in users:
        users[str(user_id)] = {"username": username, "joined": time.time()}
        _save(USERS_FILE, users)

def get_all_users():
    return list(_load(USERS_FILE).keys())

def get_forum():
    return _load(FORUM_FILE)

def create_topic(user_id, username, title, first_post_text):
    forum = get_forum()
    tid = str(int(time.time()))
    forum[tid] = {
        "title": title,
        "author_id": user_id,
        "author_name": username,
        "created": time.time(),
        "posts": [{"user_id": user_id, "username": username, "text": first_post_text, "time": time.time()}]
    }
    _save(FORUM_FILE, forum)
    return tid

def add_post(topic_id, user_id, username, text):
    forum = get_forum()
    if topic_id in forum:
        forum[topic_id]["posts"].append({"user_id": user_id, "username": username, "text": text, "time": time.time()})
        _save(FORUM_FILE, forum)
        return True
    return False

# ----- КЛАВИАТУРЫ (inline) -----
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="МЕСТА", callback_data="menu_places")],
        [InlineKeyboardButton(text="ФОРУМ", callback_data="menu_forum")],
        [InlineKeyboardButton(text="ПОИСК", callback_data="menu_search")]
    ])

def back_button(callback="main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="НАЗАД", callback_data=callback)]])

def places_categories():
    from data import PLACES
    kb = [[InlineKeyboardButton(text=val["name"], callback_data=f"cat_{key}")] for key, val in PLACES.items()]
    kb.append([InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def places_list(category_key, places, page=0):
    per_page = 5
    start = page * per_page
    end = start + per_page
    items = places[start:end]
    kb = [[InlineKeyboardButton(text=p["name"], callback_data=f"place_{category_key}_{start+i}")] for i, p in enumerate(items)]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ НАЗАД", callback_data=f"page_{category_key}_{page-1}"))
    if end < len(places):
        nav.append(InlineKeyboardButton(text="ВПЕРЕД ▶", callback_data=f"page_{category_key}_{page+1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton(text="К КАТЕГОРИЯМ", callback_data="places_back")])
    kb.append([InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def place_card_buttons(phone, lat, lon):
    kb = []
    if phone:
        kb.append(InlineKeyboardButton(text="ПОЗВОНИТЬ", url=f"tel:{phone}"))
    if lat and lon:
        kb.append(InlineKeyboardButton(text="МАРШРУТ", url=f"https://maps.google.com/?q={lat},{lon}"))
    kb.append(InlineKeyboardButton(text="НАЗАД К СПИСКУ", callback_data="back_to_list"))
    kb.append(InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))
    return InlineKeyboardMarkup(inline_keyboard=[kb])

def forum_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СПИСОК ТЕМ", callback_data="forum_list")],
        [InlineKeyboardButton(text="СОЗДАТЬ ТЕМУ", callback_data="forum_create")],
        [InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")]
    ])

def topics_list(topics, page=0):
    per_page = 5
    items = list(topics.items())[page*per_page : page*per_page+per_page]
    kb = [[InlineKeyboardButton(text=t["title"], callback_data=f"topic_{tid}")] for tid, t in items]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ НАЗАД", callback_data=f"forum_page_{page-1}"))
    if len(items) == per_page and (page+1)*per_page < len(topics):
        nav.append(InlineKeyboardButton(text="ВПЕРЕД ▶", callback_data=f"forum_page_{page+1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton(text="НАЗАД", callback_data="menu_forum")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def topic_controls(topic_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ОТВЕТИТЬ", callback_data=f"reply_{topic_id}")],
        [InlineKeyboardButton(text="К СПИСКУ ТЕМ", callback_data="forum_list")],
        [InlineKeyboardButton(text="ГЛАВНОЕ МЕНЮ", callback_data="main_menu")]
    ])

# ----- FSM состояния -----
class ForumStates(StatesGroup):
    waiting_title = State()
    waiting_first_post = State()
    waiting_reply = State()

class SearchState(StatesGroup):
    waiting_keyword = State()

# ----- ХЕНДЛЕРЫ -----
@dp.message(Command("start"))
async def start_cmd(message: Message):
    add_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    await message.answer(
        "<b>КЬЮР. ВЕЛНЕС ГИД ПО ЮЖНО-САХАЛИНСКУ</b>\n\nСПРАВОЧНИК МЕСТ, ФОРУМ, ПОИСК.\nТОЛЬКО ФАКТЫ И КОНТАКТЫ.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "main_menu")
async def main_menu_cb(call: CallbackQuery):
    await call.message.edit_text("<b>КЬЮР. ГЛАВНОЕ МЕНЮ</b>", reply_markup=main_menu(), parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "menu_places")
async def menu_places(call: CallbackQuery):
    await call.message.edit_text("<b>КАТЕГОРИИ МЕСТ</b>", reply_markup=places_categories(), parse_mode="HTML")
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
    if p.get("photos"):
        media = [InputMediaPhoto(pid) for pid in p["photos"]]
        await call.message.answer_media_group(media=media)
    text = f"<b>{p['name']}</b>\n"
    if p.get("desc"):
        text += f"<blockquote>{p['desc']}</blockquote>\n"
    if p.get("address"):
        text += f"📍 {p['address']}\n"
    if p.get("hours"):
        text += f"🕒 {p['hours']}\n"
    if p.get("price"):
        text += f"💰 {p['price']}\n"
    await call.message.answer(text, reply_markup=place_card_buttons(p.get("phone",""), p.get("lat"), p.get("lon")), parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "back_to_list")
async def back_to_list(call: CallbackQuery):
    await menu_places(call)

@dp.callback_query(F.data == "menu_forum")
async def forum_menu_cb(call: CallbackQuery):
    await call.message.edit_text("<b>ФОРУМ КЬЮР</b>\nОБЩАЙТЕСЬ, ЗАДАВАЙТЕ ВОПРОСЫ.", reply_markup=forum_menu(), parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "forum_list")
async def list_topics(call: CallbackQuery):
    forum = get_forum()
    if not forum:
        await call.message.edit_text("ТЕМ ПОКА НЕТ. БУДЬТЕ ПЕРВЫМ!", reply_markup=back_button("menu_forum"), parse_mode="HTML")
        await call.answer()
        return
    await call.message.edit_text("<b>СПИСОК ТЕМ</b>", reply_markup=topics_list(forum, 0), parse_mode="HTML")
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
    await call.message.edit_text(text, reply_markup=topic_controls(topic_id), parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "forum_create")
async def create_topic_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ForumStates.waiting_title)
    await call.message.answer("ВВЕДИТЕ НАЗВАНИЕ ТЕМЫ (НЕ БОЛЕЕ 100 СИМВОЛОВ):", reply_markup=back_button("menu_forum"))
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
    await message.answer(f"ТЕМА СОЗДАНА! ID: {topic_id}", reply_markup=forum_menu())

@dp.callback_query(F.data.startswith("reply_"))
async def start_reply(call: CallbackQuery, state: FSMContext):
    topic_id = call.data.split("_")[1]
    await state.update_data(topic_id=topic_id)
    await state.set_state(ForumStates.waiting_reply)
    await call.message.answer("ВВЕДИТЕ ТЕКСТ ОТВЕТА:", reply_markup=back_button("forum_list"))
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
        forum = get_forum()
        topic = forum[topic_id]
        text = f"<b>{topic['title']}</b>\n\n"
        for post in topic["posts"]:
            name = post["username"] or f"user_{post['user_id']}"
            text += f"<b>{name}</b> [{time.strftime('%d.%m %H:%M', time.localtime(post['time']))}]:\n{post['text']}\n\n"
        await message.answer(text[:4000], reply_markup=topic_controls(topic_id), parse_mode="HTML")
    else:
        await message.answer("ОШИБКА. ТЕМА НЕ НАЙДЕНА.", reply_markup=forum_menu())

@dp.callback_query(F.data == "menu_search")
async def search_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_keyword)
    await call.message.answer("ВВЕДИТЕ КЛЮЧЕВОЕ СЛОВО ДЛЯ ПОИСКА ПО МЕСТАМ:", reply_markup=back_button("main_menu"))
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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 