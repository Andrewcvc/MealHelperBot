import asyncio

import os 
from dotenv import load_dotenv, find_dotenv #для зчитування змінних з файлу .env
from middlewares.db import DataBaseSession
load_dotenv(find_dotenv()) #завантажуємо змінні з файлу .env
from database.engine import session_maker, create_db, drop_db

###########*не забути додати в ГІТІГНОР фаул з токеном*#############

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode

from handlers.user import user_router
from handlers.admin import admin_router
# from handlers.group import group_router


bot = Bot(os.getenv('TOKEN'), parse_mode=ParseMode.HTML)
bot.my_admin_list = []
dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(user_router)
# dp.include_router(group_router)

async def on_startup(bot):
    # await drop_db()
    await create_db()
    print('Bot started')
    
async def on_shutdown(bot):
    await drop_db()
    print('Bot stopped')
    
async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    
    await bot.delete_webhook(drop_pending_updates=True) # Скидує всі оновлення(повідомлення від користувачів в боті) які були в черзі поки бот був виключений. І дає можливість боту відповісти на останні оновлення
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    
asyncio.run(main())
    