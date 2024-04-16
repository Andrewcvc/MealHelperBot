from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.engine import session_maker
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import orm_change_banner_image, orm_get_info_pages, orm_get_banner, orm_add_banner_description

from filters.chat_types import ChatTypeFilter, IsAdmin
from keyboards.reply import get_keyboard


admin_router = Router()

ADMIN_KB = get_keyboard(
    'Додати/змінити банер',
    placeholder='Оберіть дію',
    sizes=(1,)
)

@admin_router.message(Command('admin'))
async def admin_panel(message: types.Message):
    await message.answer("Ви увійшли в адмін панель", reply_markup=ADMIN_KB)


class AddBanner(StatesGroup):
    image = State()

@admin_router.message(StateFilter(None), F.text == 'Додати/змінити банер')
async def add_banner(message: types.Message, state: FSMContext):
    async with session_maker() as session:
        pages_names = [page.name for page in await orm_get_info_pages(session)]
        await message.answer(f"Відправте фото банера. \nВ описі вкажіть для якої сторінки:\
                            \n{', '.join(pages_names)}")
        await state.set_state(AddBanner.image)
        
@admin_router.message(AddBanner.image, F.photo)
async def add_banner_image(message: types.Message, state: FSMContext):
    async with session_maker() as session:
        image_id = message.photo[-1].file_id
        for_page = message.caption.strip()
        pages_names = [page.name for page in await orm_get_info_pages(session)]
        if for_page not in pages_names:
            await message.answer(f"Такої сторінки немає. Виберіть будь ласка зі списку:\
                \n{', '.join(pages_names)}")
            return
        await orm_change_banner_image(session, for_page, image_id)
        await message.answer(f"Банер для сторінки {for_page} успішно змінено")
        await state.clear()   
        
@admin_router.message(AddBanner.image) # Якщо не фото
async def not_photo(message: types.Message):
    await message.answer("Вибачте, але я очікую фото", reply_markup=ADMIN_KB)



