
import os 
from dotenv import load_dotenv, find_dotenv #для зчитування змінних з файлу .env

load_dotenv(find_dotenv()) #завантажуємо змінні з файлу .env


from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode




bot = Bot(os.getenv('TOKEN'), parse_mode=ParseMode.HTML)
bot.my_admin_list = []
dp = Dispatcher()

def include_routers():
    from handlers.user import user_router
    from handlers.admin import admin_router
    from handlers.user_group import user_group_router

    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(user_group_router)

include_routers()

