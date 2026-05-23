from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data import CATEGORIES, CITY_NAME

def city_keyboard():
    """Выбор города (пока один)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📍 {CITY_NAME}", callback_data="city_select")]
    ])

def main_menu():
    """Главное меню (5 категорий)"""
    buttons = []
    for key, val in CATEGORIES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{val['icon']} {val['name']}",
            callback_data=f"cat_{key}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def subcategories_menu(category_key):
    """Меню подкатегорий для выбранной категории"""
    subcats = CATEGORIES[category_key]["subcats"]
    buttons = []
    for sub_key, sub_val in subcats.items():
        buttons.append([InlineKeyboardButton(
            text=sub_val["name"],
            callback_data=f"sub_{category_key}_{sub_key}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def items_list(category_key, subcat_key, items, page=0):
    """Список заведений в подкатегории (постранично, по 5)"""
    # Простой вариант без пагинации для минимализма, но если много – добавим
    # Пока просто кнопками "Назад", "В меню", "Далее"
    from math import ceil
    per_page = 5
    total = len(items)
    pages = ceil(total / per_page)
    start = page * per_page
    end = start + per_page
    page_items = items[start:end]
    
    kb = []
    for idx, item in enumerate(page_items):
        # Кнопка с названием места
        kb.append([InlineKeyboardButton(
            text=f"📍 {item['name']}",
            callback_data=f"item_{category_key}_{subcat_key}_{start+idx}"
        )])
    
    # Навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"nav_{category_key}_{subcat_key}_{page-1}"))
    if page < pages-1:
        nav.append(InlineKeyboardButton(text="Вперед ▶", callback_data=f"nav_{category_key}_{subcat_key}_{page+1}"))
    if nav:
        kb.append(nav)
    
    kb.append([InlineKeyboardButton(text="🔙 В подкатегории", callback_data=f"back_sub_{category_key}")])
    kb.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def location_phone_keyboard(address, phone, lat=None, lon=None):
    """Клавиатура для карточки места: позвонить, показать на карте"""
    buttons = []
    if phone:
        buttons.append(InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{phone}"))
    if lat and lon:
        buttons.append(InlineKeyboardButton(text="📍 Показать на карте", url=f"https://maps.google.com/?q={lat},{lon}"))
    elif address:
        # Если нет координат, но есть адрес – тоже ссылка на карту по адресу
        from urllib.parse import quote
        buttons.append(InlineKeyboardButton(text="📍 Показать на карте", url=f"https://maps.google.com/?q={quote(address)}"))
    buttons.append(InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_items"))
    buttons.append(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])