import asyncio

import os 
from dotenv import load_dotenv, find_dotenv #для зчитування змінних з файлу .env
from middlewares.db import DataBaseSession
load_dotenv(find_dotenv()) #завантажуємо змінні з файлу .env
from database.engine import session_maker, create_db, drop_db
from bot_setup import dp, bot


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
    
if __name__ == '__main__':
    asyncio.run(main())
    