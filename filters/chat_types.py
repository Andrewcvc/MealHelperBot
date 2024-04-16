from aiogram.filters import Filter
from aiogram import types, Bot


class ChatTypeFilter(Filter):
    def __init__(self, chat_types: list[str]) -> None:
        self.chat_types = chat_types

    async def __call__(self, message: types.Message) -> bool:  # Перевіряємо чи тип чату повідомлення є в списку chat_types
        return message.chat.type in self.chat_types # Повертаємо True якщо тип чату повідомлення є в списку chat_types
    
class IsAdmin(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        return message.from_user.id in bot.my_admins_list