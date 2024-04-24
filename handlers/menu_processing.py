import json
from aiogram import F, types
from aiogram.types import InputMediaPhoto, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import UserPreference
from database.orm_query import add_dishes_of_the_week, get_dishes_of_the_day, get_dishes_of_the_week, orm_get_banner, orm_get_categories, orm_get_dishes, orm_get_random_dishes
from keyboards.inline import Action, UserAction, get_callback_btns, get_day_dish_btns, get_main_menu_btn, get_user_added_btns, get_user_catalog_btns, get_user_main_btns, get_weekly_dish_btns
from sqlalchemy.exc import SQLAlchemyError




async def main_manu(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    kbds = get_user_main_btns(level=level)
    return image, kbds

##############Додати страву##############
class AddDish(StatesGroup):
    name = State()
    category = State()
    dish_for_change = None
    dish_edit = None
    text = {
        'AddDish:name': 'Введіть назву страви повторно:',
        'AddDish:category': 'Оберіть категорію ще раз:'
    }
    
class DishSettings(StatesGroup):
    id_for_delete = State()
    id_for_edit_name = State()
    edit_name = State()
    id_for_edit_category = State()
    edit_category = State()
    pick_category = State()
    pick_count = State()
    category_id = None
    text = {'DishSettings:id_for_edit_name': 'Введіть номер страви, назву якої ви хочете відредагувати'}


async def add_dish(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    kbds = get_main_menu_btn(level=level)
    return image, kbds
    

###########Каталог страв##############
    
async def catalog(session, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    
    categories = await orm_get_categories(session)
    kbds = get_callback_btns(btns={**{category.name: f'category_{category.id}' for category in categories}, "Головне меню🏠": UserAction(action=Action.main).pack()})
    return image, kbds

##############*Страва дня##############


async def dish_of_the_day(session, user_id, menu_name):
    banner = await orm_get_banner(session, menu_name)
    dishes_of_the_day = await get_dishes_of_the_day(session, user_id)

    if dishes_of_the_day:
        category_map = {}
        for dish in dishes_of_the_day:
            category = dish.dish.category.name
            if category not in category_map:
                category_map[category] = []
            category_map[category].append(dish.dish.name)
    
        dishes_list = [f"<strong>{category}:</strong>\n- " + '\n- '.join(names) for category, names in category_map.items()]
        caption = f"Ваш список на сьогодні:\n\n{'\n\n'.join(dishes_list)}"
    else:
        caption = "На сьогодні страви дня відсутні"
    
    image = InputMediaPhoto(media=banner.image, caption=caption)
    kbds = get_day_dish_btns()
    
    return image, kbds

##############*Меню на тиждень##############
async def dishes_of_the_week(session, user_id, menu_name):
    banner = await orm_get_banner(session, menu_name)
    dishes_of_the_week = await get_dishes_of_the_week(session, user_id)
    
    if dishes_of_the_week:
        category_map = {}
        for dish in dishes_of_the_week:
            category = dish.dish.category.name
            if category not in category_map:
                category_map[category] = []
            category_map[category].append(dish.dish.name)
    
        dishes_list = [f"<strong>{category}:</strong>\n- " + '\n- '.join(names) for category, names in category_map.items()]
        caption = f"Ваш список на тиждень:\n\n{'\n\n'.join(dishes_list)}"
    else:
        caption = "<strong>Список страв на тиждень відсутній.</strong>\n\nЩоб його згенерувати, задайте ваш алгоритм підбору страв, а потім натисність <strong>'Згенерувати страви🍽️'</strong>"
    
    image = InputMediaPhoto(media=banner.image, caption=caption)
    kbds = get_weekly_dish_btns()
    
    return image, kbds


async def generate_weekly_menu(session: AsyncSession, user_id: int, preferences: dict):
    menu = []
    for category_id, count in preferences.items():
        try:
            dishes = await orm_get_random_dishes(session, int(category_id), int(count))
            menu.extend(dishes)
        except SQLAlchemyError as e:
            print(f"Failed to retrieve dishes for category {category_id}: {e}")
    
    if menu:
        await add_dishes_of_the_week(session, user_id, menu)
    return menu

def format_menu(dishes):
    # Format the menu for display
    return '\n'.join([f"{dish.category.name}: {dish.name}" for dish in dishes])


##############*Обробка меню##############

async def get_menu_content(
    session: AsyncSession,
    level: int,
    menu_name: str,
    category: int | None = None,
    page: int | None = None,
    user_id: int | None = None
    ):
    
    if level == 0: # main
        return await main_manu(session, level, menu_name)
    elif level == 1: # add_dish
        return await add_dish(session, level, menu_name)
    elif level == 2: # dish_list_starting_page
        return await catalog(session, menu_name)
    

