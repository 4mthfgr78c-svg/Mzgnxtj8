from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="МЕСТА", callback_data="menu_places")],
        [InlineKeyboardButton(text="ФОРУМ", callback_data="menu_forum")],
        [InlineKeyboardButton(text="ПОИСК", callback_data="menu_search")]
    ])

def back_button(callback="main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="НАЗАД", callback_data=callback)]
    ])

def places_categories():
    from data import PLACES
    kb = []
    for key, val in PLACES.items():
        kb.append([InlineKeyboardButton(text=val["name"], callback_data=f"cat_{key}")])
    kb.append([InlineKeyboardButton(text="НАЗАД", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def places_list(category_key, places, page=0):
    per_page = 5
    start = page * per_page
    end = start + per_page
    items = places[start:end]
    kb = []
    for i, p in enumerate(items):
        kb.append([InlineKeyboardButton(text=p["name"], callback_data=f"place_{category_key}_{start+i}")])
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
    start = page * per_page
    items = list(topics.items())[start:start+per_page]
    kb = []
    for tid, t in items:
        kb.append([InlineKeyboardButton(text=t["title"], callback_data=f"topic_{tid}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ НАЗАД", callback_data=f"forum_page_{page-1}"))
    if len(items) == per_page and start+per_page < len(topics):
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