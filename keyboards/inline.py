from enum import Enum
from aiogram import types
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from keyboards.reply import get_keyboard

class Action(str, Enum):
    BACK = 'back'
    DELETE = 'delete'
    EDIT = 'edit'
    CANCLE = 'cancle'
    add_dish = 'add_dish'
    main = 'main_page'
    dish_list = 'dish_list'
    edit_name = 'edit_name'
    edit_category = 'edit_category'
    dish_of_the_day = 'dish_of_the_day'
    dish_day = 'dish_day'
    del_dish_day = 'del_dish_day'

class UserAction(CallbackData, prefix="act"):
    action: Action

class MenuCallBack(CallbackData, prefix="menu"):
    level: int
    menu_name: str
    category: int | None = None
    page: int = 1
    product_id: int | None = None

def get_user_main_btns(*, level:int, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()
    btns = {
        "Додати страву🍲" : "add_dish",
        "Список страв🧾" : "dish_list",
        "Меню на тиждень🍽️" : "menu_for_week", 
        "Страва дня🍳" : "dish_of_the_day",           
        "Залишити відгук📝" : "feedback",
    }

    for text, menu_name in btns.items():
        if menu_name == 'add_dish':
            keyboard.add(InlineKeyboardButton(text=text, callback_data=MenuCallBack(level=level+1, menu_name=menu_name).pack())) #pack() - метод для упаковки даних в строку
        elif menu_name == 'dish_list':
            keyboard.add(InlineKeyboardButton(text=text, callback_data=MenuCallBack(level=2, menu_name=menu_name).pack()))
        elif menu_name == 'menu_for_week':
            keyboard.add(InlineKeyboardButton(text=text, callback_data=MenuCallBack(level=3, menu_name=menu_name).pack()))
        elif menu_name == 'dish_of_the_day':
            keyboard.add(InlineKeyboardButton(text=text, callback_data=UserAction(action=Action.dish_of_the_day).pack()))
        else:
            keyboard.add(InlineKeyboardButton(text=text, callback_data=MenuCallBack(level=level, menu_name=menu_name).pack()))
    return keyboard.adjust(*sizes).as_markup()

#Клавіатура для початкової сторінки add_dish
def get_main_menu_btn(*, level: int, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Головне меню🏠", callback_data=MenuCallBack(level=level-1, menu_name='main').pack()))
    return keyboard.row().as_markup()

#Клавіатура для сторінки зі списком страв

def get_dish_list_btns(sizes: tuple[int] = (2, )
):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Видалити страву❌", callback_data=UserAction(action=Action.DELETE).pack()))
    keyboard.add(InlineKeyboardButton(text="Редагувати страву✏️", callback_data=UserAction(action=Action.EDIT).pack()))
    keyboard.add(InlineKeyboardButton(text="Додати страву🍲", callback_data=UserAction(action=Action.add_dish).pack()))
    keyboard.add(InlineKeyboardButton(text="Головне меню🏠", callback_data=UserAction(action=Action.main).pack()))
    keyboard.add(InlineKeyboardButton(text="Категорії страв🧾", callback_data=UserAction(action=Action.dish_list).pack()))
    
    return keyboard.adjust(*sizes).as_markup()

#Клавіатура для сторінки з пустим списком страв
def get_empty_list_btns(sizes: tuple[int] = (2, )
):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Додати страву🍲", callback_data=UserAction(action=Action.add_dish).pack()))
    keyboard.add(InlineKeyboardButton(text="Головне меню🏠", callback_data=UserAction(action=Action.main).pack()))
    keyboard.add(InlineKeyboardButton(text="Категорії страв🧾", callback_data=UserAction(action=Action.dish_list).pack()))
    
    return keyboard.adjust(*sizes).as_markup()

#Клавіатура для редагування
def get_edit_btns(sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Назву✏️", callback_data=UserAction(action=Action.edit_name).pack()))
    keyboard.add(InlineKeyboardButton(text="Категорію📁", callback_data=UserAction(action=Action.edit_category).pack()))
    keyboard.add(InlineKeyboardButton(text="Відмінити❌", callback_data=UserAction(action=Action.CANCLE).pack()))
    return keyboard.adjust(*sizes).as_markup()

#Кнопка відмінити
def get_cancle_btn(sizes: tuple[int] = (1, )):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Відмінити❌", callback_data=UserAction(action=Action.CANCLE).pack()))
    return keyboard.adjust(*sizes).as_markup()

#Клавіатура після того як страву додано
def get_user_added_btns(sizes: tuple[int] = (2, )):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Головне меню🏠", callback_data=UserAction(action=Action.main).pack()))
    keyboard.add(InlineKeyboardButton(text="Додати нову страву🍲", callback_data=UserAction(action=Action.add_dish).pack()))
    keyboard.add(InlineKeyboardButton(text="Категорії страв🧾", callback_data=UserAction(action=Action.dish_list).pack()))
    return keyboard.adjust(*sizes).as_markup()

def get_user_catalog_btns(*, level: int, categories: list, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()
    
    for c in categories:
        keyboard.add(InlineKeyboardButton(text=c.name, callback_data=MenuCallBack(level=level+2, menu_name=c.name, category=c.id).pack()))
    keyboard.add(InlineKeyboardButton(text="Головне меню🏠", callback_data=UserAction(action=Action.main).pack()))
    return keyboard.adjust(*sizes).as_markup()

def get_dishes_btns( 
    *,
    level: int,
    category: int,
    page: int,
    pagination_btns: dict,
    sizes: tuple[int] = (2, 1),
):
    keyboard = InlineKeyboardBuilder()    
    row = []
    for text, menu_name in pagination_btns.items():
        if menu_name == 'next':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name=menu_name,
                                                category=category,
                                                page=page+1).pack()))
        elif menu_name == 'previous':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name=menu_name,
                                                category=category,
                                                page=page-1).pack()))
    return keyboard.row(*row).as_markup()    #row() - метод для добавления кнопок в строку

#Клавіатура страви дня
def get_day_dish_btns(sizes: tuple[int] = (2, )):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Згенерувати блюдо🍲", callback_data=UserAction(action=Action.dish_day).pack()))
    keyboard.add(InlineKeyboardButton(text="Очистити список🗑️", callback_data=UserAction(action=Action.del_dish_day).pack()))
    keyboard.add(InlineKeyboardButton(text="Головне меню🏠", callback_data=UserAction(action=Action.main).pack()))
    
    return keyboard.adjust(*sizes).as_markup()

def get_callback_btns(
    *,
    btns: dict[str, str],
    sizes: tuple[int] = (2,)):
    
    keyboard = InlineKeyboardBuilder()

    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))
    return keyboard.adjust(*sizes).as_markup()
