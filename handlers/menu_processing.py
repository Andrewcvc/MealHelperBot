from aiogram import F, types
from aiogram.types import InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.orm_query import orm_get_banner, orm_get_categories, orm_get_dishes
from keyboards.inline import Action, UserAction, get_callback_btns, get_dishes_btns, get_main_menu_btn, get_user_catalog_btns, get_user_main_btns
from utils.paginator import Paginator



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

# def pages(paginator: Paginator):
#     btns = dict()
#     if paginator.has_previous():
#         btns["Попередня◀️"] = "previous"
#     if paginator.has_next():
#         btns["Наступна▶️"] = "next"
#     return btns

# async def  dishes(session, level, category, page):
#     dishes = await orm_get_dishes(session, category_id=category)
#     paginator = Paginator(dishes, page=page)
#     dish = paginator.get_page()[0]
#     dish_names = f"<strong>{dish.name}</strong>\n<strong>Сторінка {paginator.page} з {paginator.pages}</strong>"
    
#     pagination_btns = pages(paginator)
    
#     kbds = get_dishes_btns(
#         level=level,
#         category=category,
#         page=page,
#         pagination_btns=pagination_btns,
#     )
    
#     return dish_names, kbds
    
##############Обробка меню##############

async def get_menu_content(
    session: AsyncSession,
    level: int,
    menu_name: str,
    category: int | None = None,
    page: int | None = None,
    ):
    
    if level == 0: # main
        return await main_manu(session, level, menu_name)
    elif level == 1: # add_dish
        return await add_dish(session, level, menu_name)
    elif level == 2: # dish_list_starting_page
        return await catalog(session, menu_name)
    

