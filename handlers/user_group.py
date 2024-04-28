from string import punctuation
from aiogram import F, types, Router, Bot
from filters.chat_types import ChatTypeFilter
from aiogram.filters import Command

user_group_router = Router()
user_group_router.message.filter(ChatTypeFilter(['group', 'supergroup'])) # Встановлюємо фільтр для групових чатів

@user_group_router.message(Command('bot'))
async def get_admins(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    admins_list = await bot.get_chat_administrators(chat_id)
    admins_list = [
        member.user.id
        for member in admins_list
        if member.status == "creator" or member.status == "administrator"
    ]
    bot.my_admins_list = admins_list