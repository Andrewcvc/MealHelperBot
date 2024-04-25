import json
import traceback

from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command, or_f, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputMediaPhoto
from sqlalchemy.exc import SQLAlchemyError


from bot_setup import bot
from database.engine import session_maker
from database.models import UserPreference
from handlers.menu_processing import AddDish, DishSettings, catalog, dish_of_the_day, dishes_of_the_week, format_menu, generate_weekly_menu, get_menu_content, get_page_photo, update_media_for_page
from keyboards.inline import Action, MenuCallBack, UserAction, get_algorithm_settings_btns, get_callback_btns, get_cancle_btn, get_day_dish_btns, get_dish_list_btns, get_edit_btns, get_empty_list_btns, get_user_added_btns, get_weekly_dish_btns

from database.orm_query import add_random_dish_of_the_day, clear_dishes_of_the_day, clear_dishes_of_the_week, get_dishes_of_the_day, orm_add_dish, orm_add_user, orm_clear_user_preferences, orm_delete_dish, orm_get_banner, orm_get_categories, orm_get_categories_by_ids, orm_get_dish, orm_get_dishes, orm_get_user_preferences, orm_update_dish, orm_update_user_preferences




user_router = Router()

@user_router.message(CommandStart())
async def start_cmd(message: types.Message):
    async with session_maker() as session:
        user = message.from_user
        await orm_add_user(
            session,
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            user_name=user.username,
            phone=None,
        )
        media, reply_markup = await get_menu_content(session, level=0, menu_name='main')
        await message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)
    

##################*ADD DISH PAGE FSM##################

@user_router.callback_query(StateFilter(None), MenuCallBack(level=1, menu_name='add_dish').filter())
async def add_dish_name(callback:types.CallbackQuery, callback_data:MenuCallBack, state:FSMContext):
    async with session_maker() as session:
        media, reply_markup = await get_menu_content(
            session,
            level=callback_data.level,
            menu_name=callback_data.menu_name,
            category=callback_data.category,
            page=callback_data.page,
        )
        sent_message = await callback.message.edit_media(media=media, reply_markup=reply_markup)
        await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state(AddDish.name)
        await callback.answer()
        

async def go_back(callback: types.CallbackQuery, state: FSMContext):
    async with session_maker() as session:
        current_state = await state.get_state()  
    # Шукаємо індекс поточного стану в списку всіх станів
        state_index = AddDish.__all_states__.index(current_state) if current_state in AddDish.__all_states__ else -1
        if state_index == 0 or state_index == -1:
            await update_media_for_page(session, callback, 'add_dish', 'Кроків назад вже немає. Додайте назву страви.')
            return
    # Встановлюємо попередній стан
        previous_state = AddDish.__all_states__[state_index - 1]
        await state.set_state(previous_state)
        caption = f'Ви повернулись на крок назад. \n{AddDish.text[previous_state]}'
        await update_media_for_page(session, callback, 'add_dish', caption)

@user_router.message(AddDish.name, F.text)
async def add_dish_name(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    last_bot_message_id = user_data.get('last_bot_message_id')
    
    async with session_maker() as session:
        
        await state.update_data(name=message.text)
        await message.delete()
        
        categories = await orm_get_categories(session)
        btns = {category.name: str(category.id) for category in categories}
        btns['Назад'] = Action.BACK
        btns['Повернутись в головне меню🏠'] = UserAction(action=Action.main).pack()
        menu_name = 'add_dish'
        caption = f'<strong>Оберіть категорію для "{message.text}":</strong>'
        image = await get_page_photo(session, menu_name, caption)
        formatted_media = InputMediaPhoto(media=image.media, caption=caption)
        
        if last_bot_message_id:
            await bot.edit_message_media(
                media=formatted_media,
                chat_id=message.chat.id,
                message_id=last_bot_message_id,
                reply_markup=get_callback_btns(btns=btns)
            )
        await state.set_state(AddDish.category)
        
@user_router.message(AddDish.name)
async def add_dish_name(message: types.Message, state: FSMContext):
    await message.answer('<strong>Ви вказали некоректну назву товару. Введіть назву страви повторно:</strong>')
        
    
@user_router.callback_query(AddDish.category)
async def category_choice(callback:types.CallbackQuery, state:FSMContext):
    user_id = callback.from_user.id
    async with session_maker() as session:
        if callback.data == Action.BACK:
            await go_back(callback, state)
        elif callback.data == UserAction(action=Action.main).pack():
            await get_main_page(callback, state)
        else:
            categories = await orm_get_categories(session)
            if int(callback.data) in [category.id for category in categories]:
                await state.update_data(category=callback.data)
                data = await state.get_data()
                await orm_add_dish(session, user_id=user_id, data=data)
                caption = '<strong>Страву додано</strong>'
                reply_markup = get_user_added_btns(sizes=(2,))
                await update_media_for_page(session, callback, 'add_dish', caption, reply_markup)
                await callback.answer()
                await state.clear()
            else:
                await callback.answer('<strong>Виберіть категорію зі списку</strong>', show_alert=True)
                return


@user_router.message(AddDish.category, F.text)
async def delete_user_message(message: types.Message):
    await message.edit_text('<strong>Виберіть категорію зі списку вище</strong>')



##################*DISH LIST PAGE##################


@user_router.callback_query(F.data.startswith('category_'))
async def starring_at_dish(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    category_id = callback.data.split('_')[-1]
    
    
    async with session_maker() as session:
        categories = await orm_get_categories(session)
        for category in categories:
            if category.id == int(callback.data.split('_')[-1]):
                category_name = category.name
        
        await state.update_data(category_id=category_id)
        dishes = await orm_get_dishes(session, user_id=user_id, category_id=category_id)
        if not dishes:
            caption = "В цій категорії поки що немає страв"
            reply_markup = get_empty_list_btns(sizes=(2,))
            await update_media_for_page(session, callback, 'dish_list', caption, reply_markup)
        else:
            dish_list = ""
            for i, dish in enumerate(dishes):
                dish_list += f"{i+1}) {dish.name}\n"
            reply_markup=get_dish_list_btns(sizes=(2,))
            text = f'<strong>Ось список страв з категорії\n"<b>{category_name}:</b>"</strong>'
            caption = f"{text}\n\n{dish_list.strip()}"
            await update_media_for_page(session, callback, 'dish_list', caption, reply_markup)
        await callback.answer()

###################*DISH_OF_THE_DAY###################

@user_router.callback_query(UserAction.filter(F.action == Action.dish_of_the_day))
async def dish_of_the_day_page(callback: types.CallbackQuery):    
    user_id = callback.from_user.id
    async with session_maker() as session:
        media, reply_markup = await dish_of_the_day(session, user_id, menu_name='dish_of_the_day')
        try:
            await callback.message.edit_media(media=media, reply_markup=reply_markup)
        except Exception as e:
            print(f"Failed to edit media: {e}")
            await callback.message.delete()
            await callback.message.answer_photo(photo=media.media, caption=media.caption, reply_markup=reply_markup)
        await callback.answer()

@user_router.callback_query(UserAction.filter(F.action == Action.dish_day))
async def category_dish_day(callback: types.CallbackQuery, state: FSMContext):
    
    async with session_maker() as session:
        categories = await orm_get_categories(session)
        reply_markup = get_callback_btns(btns={**{category.name: f'DayCategory_{category.id}' for category in categories}, "Головне меню🏠": UserAction(action=Action.main).pack()}) 
        caption = '<strong>Оберіть категорію для страви дня:</strong>'
        await update_media_for_page(session, callback, 'dish_of_the_day', caption, reply_markup)
        await callback.answer()

@user_router.callback_query(F.data.startswith('DayCategory_'))
async def add_dish_day(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    category_id = int(callback.data.split('_')[-1])
    
    async with session_maker() as session:
        await state.update_data(category_id=category_id)
        random_dish = await add_random_dish_of_the_day(session, user_id=user_id, category_id=category_id)
        if not random_dish:
            categories = await orm_get_categories(session)
            reply_markup = get_callback_btns(btns={**{category.name: f'DayCategory_{category.id}' for category in categories}, "Головне меню🏠": UserAction(action=Action.main).pack()})
            caption = "В цій категорії поки що немає страв. Виберіть іншу:"
            await update_media_for_page(session, callback, 'dish_of_the_day', caption, reply_markup)
        else:
            categories = await orm_get_categories(session)
            for catagory in categories:
                if catagory.id == category_id:
                    category_name = catagory.name
            caption = f'<strong>{category_name}:\n"{random_dish.name}"</strong>'
            reply_markup = get_callback_btns(
                btns={
                    "Страви дня🍳": UserAction(action=Action.dish_of_the_day).pack(),
                    "Згенерувати ще🍲": UserAction(action=Action.dish_day).pack(),
                    'Головне меню🏠': UserAction(action=Action.main).pack()
                    })
            await update_media_for_page(session, callback, 'dish_of_the_day', caption, reply_markup)
        await callback.answer()

@user_router.callback_query(UserAction.filter(F.action == Action.del_dish_day))
async def delete_dish_day(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with session_maker() as session:
        await clear_dishes_of_the_day(session, user_id=user_id)
        media, reply_markup = await dish_of_the_day(session, user_id, menu_name='dish_of_the_day')
        formatted_media = InputMediaPhoto(media=media.media, caption=media.caption)
        
        await callback.message.edit_media(media=formatted_media, reply_markup=reply_markup)
        await callback.answer()
        

##################*Menu_For_Week##################
@user_router.callback_query(UserAction.filter(F.action == Action.menu_for_week))
async def dishes_of_the_week_page(callback: types.CallbackQuery):    
    user_id = callback.from_user.id
    async with session_maker() as session:
        media, reply_markup = await dishes_of_the_week(session, user_id, menu_name='menu_for_week')
        try:
            await callback.message.edit_media(media=media, reply_markup=reply_markup)
        except Exception as e:
            print(f"Failed to edit media: {e}")
            await callback.message.delete()
            await callback.message.answer_photo(photo=media.media, caption=media.caption, reply_markup=reply_markup)
        await callback.answer()

##################*ALGORITHM SETTINGS##################

@user_router.callback_query(UserAction.filter(F.action == Action.algorithm_settings))
async def algorithm_settings(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with session_maker() as session:
        preferences = await orm_get_user_preferences(session, user_id)
        if preferences:
            category_ids = list(map(int, preferences.keys()))
            categories = await orm_get_categories_by_ids(session, category_ids)
            category_map = {category.id: category.name for category in categories}

            response_lines = [
                f"<strong>{category_map[int(category_id)]}: {preferences[category_id]}</strong>"
                for category_id in preferences
            ]
            caption = 'Ваш алгоритм:\n\n' + '\n'.join(response_lines)
            reply_markup = get_algorithm_settings_btns()
            await update_media_for_page(session, callback, 'menu_for_week', caption, reply_markup)
        else:
            caption = "Алгоритм не заданий. Натисніть на кнопку 'Задати алгоритм'."
            reply_markup = get_algorithm_settings_btns()
            await update_media_for_page(session, callback, 'menu_for_week', caption, reply_markup)
    await callback.answer()

##################*SET ALGORITHM FSM##################

@user_router.callback_query(UserAction.filter(F.action == Action.set_algorithm))
async def set_algorithm(callback: types.CallbackQuery, state: FSMContext):
    async with session_maker() as session:
        categories = await orm_get_categories(session)
        reply_markup = get_callback_btns(btns={**{category.name: f'WeeklyCategory_{category.id}' for category in categories}, "Головне меню🏠": UserAction(action=Action.main).pack()})
        caption = '<strong>Оберіть категорію:</strong>'
        await update_media_for_page(session, callback, 'menu_for_week', caption, reply_markup)
        await state.set_state(DishSettings.pick_category) 
        await callback.answer()

@user_router.callback_query(F.data.startswith('WeeklyCategory_'))
async def add_weekly_category(callback: types.CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split('_')[-1])
    async with session_maker() as session:
        menu_name = 'menu_for_week'
        reply_markup = get_callback_btns(btns={'Відмінити❌': UserAction(action=Action.menu_for_week).pack()})
        caption = '<strong>Введіть кількість страв для цієї категорії:</strong>'
        image = await get_page_photo(session, menu_name, caption)
        formatted_media = InputMediaPhoto(media=image.media, caption=caption)
        sent_message = await callback.message.edit_media(media=formatted_media, reply_markup=reply_markup)
        await state.update_data(category_id=category_id, last_bot_message_id=sent_message.message_id)
        await state.set_state(DishSettings.pick_count)
        await callback.answer()
    

@user_router.message(DishSettings.pick_count, F.text)
async def add_weekly_count(message: types.Message, state: FSMContext):
    try:
        async with session_maker() as session:
            user_id = message.from_user.id
            count_text = message.text
            count = int(count_text)
            menu_name = 'menu_for_week'
            
            data = await state.get_data()
            category_id = data.get('category_id')
            last_bot_message_id = data.get('last_bot_message_id')
            preferences = {str(category_id): count}
            
            await message.delete()
            if not count_text.isdigit():
                caption = "Будь ласка введіть лише цифри. Спробуйте ще раз."
                image = await get_page_photo(session, menu_name, caption)
                formatted_media = InputMediaPhoto(media=image.media, caption=caption)
                await message.edit_media(media=formatted_media)
                return

            await orm_update_user_preferences(session, user_id, preferences)
            caption = '<strong>Категорія та кількість страв збережені</strong>'
            reply_markup=get_callback_btns(btns={'Задати ще категорію⚙️': UserAction(action=Action.set_algorithm).pack(), 'Меню на тиждень🍽️': UserAction(action=Action.menu_for_week).pack()})
            image = await get_page_photo(session, menu_name, caption)
            formatted_media = InputMediaPhoto(media=image.media, caption=caption)
            
            if last_bot_message_id:
                await bot.edit_message_media(
                    media=formatted_media,
                    chat_id=message.chat.id,
                    message_id=last_bot_message_id,
                    reply_markup=reply_markup
                )
            
            await state.clear()
    except SQLAlchemyError as e:
        await message.answer("An error occurred while updating your preferences.")

##################*Clear Algorithm##################

@user_router.callback_query(UserAction.filter(F.action == Action.clear_algorithm))
async def clear_algorithm(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with session_maker() as session:
        result = await orm_clear_user_preferences(session, user_id)
        if result:
            caption = "Ваші налаштування були успішно скинуті."
        else:
            caption = "Не вдалося скинути налаштування. Спробуйте пізніше."
        reply_markup=get_callback_btns(btns={"Задати новий алгоритм⚙️": UserAction(action=Action.set_algorithm).pack()})
        await update_media_for_page(session, callback, 'menu_for_week', caption, reply_markup)
    await callback.answer()

##################*DISPLAY WEEKLY MENU##################

@user_router.callback_query(UserAction.filter(F.action == Action.dish_of_the_week))
async def display_weekly_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with session_maker() as session:
        
        preferences = await orm_get_user_preferences(session, user_id)
        if not preferences:
            await callback.message.answer("Алгоритм не заданий. Натисніть на кнопку 'Задати алгоритм'.", reply_markup=get_callback_btns(btns={'Задати алгоритм⚙️': UserAction(action=Action.set_algorithm).pack()}))
            await callback.answer()
        weekly_menu = await generate_weekly_menu(session, user_id, preferences)

        if not weekly_menu:
            await callback.message.answer("Вибачте, але меню на тиждень не згенеровано. Спробуйте ще раз.")
            await callback.answer()
        else:
            category_map = {}
            for dish in weekly_menu:
                category = dish.category.name
                if category not in category_map:
                    category_map[category] = []
                category_map[category].append(dish.name)
    
            dishes_list = [f"<strong>{category}:</strong>\n- " + '\n- '.join(names) for category, names in category_map.items()]
            caption = f"Ваш список на тиждень:\n\n{'\n\n'.join(dishes_list)}"
            banner = await orm_get_banner(session, 'menu_for_week')
            media = InputMediaPhoto(media=banner.image, caption=caption)
            kbds = get_weekly_dish_btns()
            await callback.message.edit_media(media=media, caption=caption, reply_markup=kbds)
            await callback.answer()

##################*CLEAR WEEKLY MENU##################
@user_router.callback_query(UserAction.filter(F.action == Action.del_weekly_dishes))
async def clear_weekly_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with session_maker() as session:
        await clear_dishes_of_the_week(session, user_id=user_id)
        media, reply_markup = await dishes_of_the_week(session, user_id, menu_name='menu_for_week')
        formatted_media = InputMediaPhoto(media=media.media, caption=media.caption)
        await callback.message.edit_media(media=formatted_media, reply_markup=reply_markup)
        
        await callback.answer()

############*Обробка кнопок################


##################*DELETE DISH BTN FSM##################
#Обробка кнопки Видалити страву
@user_router.callback_query(UserAction.filter(F.action==Action.DELETE))
async def delete_dish(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(message_id_to_delete=callback.message.message_id)
    await callback.message.edit_text("<strong>Введіть номер страви, яку ви хочете видалити</strong>", reply_markup=get_cancle_btn(sizes=(1,)))
    await callback.answer()
    await state.set_state(DishSettings.id_for_delete)


@user_router.message(DishSettings.id_for_delete, F.text)
async def delete_dish_by_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with session_maker() as session:
        user_data = await state.get_data()
        categotry_id = user_data.get('category_id')
        message_id_to_delete = user_data.get('message_id_to_delete')
        dishes = await orm_get_dishes(session, user_id=user_id, category_id=categotry_id)
        
        if message_id_to_delete:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id_to_delete)
                
            
        dish_index = message.text.isdigit() and int(message.text) - 1
        if 0 <= dish_index < len(dishes): # Перевірка чи введений номер страви є в межах списку
            dish = dishes[dish_index]
            await orm_delete_dish(session, user_id=user_id, dish_id=dish.id)
            await message.answer(f"<strong>Страву '{dish.name}' видалено!\nОсь оновлений список:</strong>")
            dishes = await orm_get_dishes(session, user_id=user_id, category_id=categotry_id)
            if dishes:
                for i, updated_dish in enumerate(dishes):
                    await message.answer(f"<strong>{i+1}) {updated_dish.name}</strong>")
            else:
                await message.answer("<strong>В цій категорії поки що немає страв</strong>", reply_markup=get_empty_list_btns(sizes=(2,)))
        else:
            await message.answer("<strong>Введіть коректний номер страви</strong>")
            
        await message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))

#############################################################

##################*EDIT DISH BTN FSM##################

@user_router.callback_query(UserAction.filter(F.action == Action.EDIT))
async def edit_btns(callback: types.CallbackQuery):
    await callback.message.edit_text("<strong>Що саме ви хочете змінити:</strong>", reply_markup=get_edit_btns(sizes=(2,)))

#Обробка кнопки Змінити назву

@user_router.callback_query(UserAction.filter(F.action == Action.edit_name))
async def edit_dish_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("<strong>Введіть номер страви, назву якої ви хочете відредагувати</strong>", reply_markup=get_cancle_btn(sizes=(1,)))
    await state.update_data(message_id_to_delete=callback.message.message_id)
    await callback.answer()
    await state.set_state(DishSettings.id_for_edit_name)


@user_router.message(DishSettings.id_for_edit_name, F.text)
async def edit_dish_by_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    dish_index = message.text.isdigit() and int(message.text) - 1
    data = await state.get_data()
    message_id_to_delete = data.get('message_id_to_delete')
    
    if message_id_to_delete:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id_to_delete)
        
    async with session_maker() as session:
        user_data = await state.get_data()
        category_id = user_data.get('category_id')
        dishes = await orm_get_dishes(session, user_id=user_id, category_id=category_id)
        
        if 0 <= dish_index < len(dishes):
            dish = dishes[dish_index]
            await state.update_data(dish_id_for_edit=dish.id)
            await message.answer(f"<strong>Введіть нову назву для страви: '{dish.name}'</strong>", reply_markup=get_callback_btns(btns={'Назад': UserAction(action=Action.BACK).pack()}))
            await state.set_state(DishSettings.edit_name)
        else:
            await message.answer("<strong>Введіть коректний номер страви</strong>")
            await message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))


@user_router.callback_query(UserAction.filter(F.action == Action.BACK))
async def go_back_edit_category(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == DishSettings.id_for_edit_name:
        await callback.answer('Кроків назад вже немає.')
        return
    previous_state = None
    for step in DishSettings.__all_states__:
        if step.state == current_state:
            await state.set_state(previous_state)
            await callback.message.edit_text(f'{DishSettings.text[previous_state]}', reply_markup=get_cancle_btn(sizes=(2,)))
            return
        previous_state = step



@user_router.message(DishSettings.edit_name, F.text)
async def edit_dish_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    category_id = user_data.get('category_id')
    dish_id = user_data.get('dish_id_for_edit')

    if len(message.text) < 3:
        await message.answer("Назва страви повинна бути від 3 символів.\n Введіть назву товару повторно:")
        return
    
    async with session_maker() as session:
        try:
            await orm_update_dish(session, user_id=user_id, dish_id=dish_id, data={'name': message.text, 'category': category_id})
            dishes = await orm_get_dishes(session, user_id=user_id, category_id=category_id)
            await message.answer(f"<strong>Назву успішно змінено!\nОсь оновлений список:</strong>")
            for i, dish in enumerate(dishes):
                await message.answer(f"<strong>{i+1}) {dish.name}</strong>")
            await message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))
        except Exception as e:
            await message.answer(f"<strong>Помилка при змінні назви:</strong> \n{str(e)}")
            await message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))
            await state.clear()


@user_router.message(DishSettings.edit_name)
async def add_dish_name(message: types.Message):
    await message.answer('<strong>Ви вказали некоректну назву товару. Введіть назву страви повторно:</strong>')
        
#Обробка кнопки Змінити Категорію

@user_router.callback_query(UserAction.filter(F.action == Action.edit_category))
async def edit_dish_category_by_id(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("<strong>Введіть номер страви, категорію якої ви хочете змінити</strong>", reply_markup=get_cancle_btn(sizes=(1,)))
    await callback.answer()
    await state.set_state(DishSettings.id_for_edit_category)
    
@user_router.message(DishSettings.id_for_edit_category, F.text)
async def edit_dish_category(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    category_id = user_data.get('category_id')
    
    async with session_maker() as session:
        dishes = await orm_get_dishes(session, user_id=user_id, category_id=category_id)
        dish_index = message.text.isdigit() and int(message.text) - 1
        
        if 0 <= dish_index < len(dishes):
            dish = dishes[dish_index]
            await state.update_data(dish_id_for_edit=dish.id)
            await state.update_data(name=dish.name)
            categories = await orm_get_categories(session)
            btns = {category.name: str(category.id) for category in categories}
            btns['Назад'] = UserAction(action=Action.BACK).pack()
            btns['Повернутись в головне меню🏠'] = UserAction(action=Action.main).pack()
            await message.answer(f'<strong>Оберіть нову категорію для "{dish.name}":</strong>', reply_markup=get_callback_btns(btns=btns))
            await state.set_state(DishSettings.edit_category)
        else:
            await message.answer("<strong>Введіть коректний номер страви</strong>")
            await message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))


@user_router.callback_query(DishSettings.edit_category)
async def category_rechoice(callback:types.CallbackQuery, state:FSMContext):
    user_id = callback.from_user.id
    dish_data = await state.get_data()
    dish_name = dish_data.get('name')
    dish_id = dish_data.get('dish_id_for_edit')
    
    async with session_maker() as session:
        categories = await orm_get_categories(session)
        category_ids = [category.id for category in categories]
        
        if callback.data == UserAction(action=Action.main).pack():
            await get_main_page(callback, state)
        elif int(callback.data) in category_ids:
            await callback.answer()
            await state.update_data(name=dish_name)
            await state.update_data(category=callback.data)
        else:
            await callback.answer('<strong>Виберіть категорію зі списку</strong>')
            await callback.answer()
            return
        data = await state.get_data()
        try:
            if dish_id and 'category' in data:
                await orm_update_dish(session, user_id, dish_id, data)
                await callback.message.answer(f'<strong>Категорію для "{dish_name}" успішно змінено!</strong>', reply_markup=get_callback_btns(
                    btns={
                        'Головне меню🏠': UserAction(action=Action.main).pack(),
                        'Категорії страв🧾': UserAction(action=Action.dish_list).pack(),
                        }
                    ))
                await state.clear()
        except Exception as e:
            await callback.message.answer(f"<strong>Помилка при оновленні категорії: \n{str(e)}</strong>")
            await callback.message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))
            await state.clear()

#Обробка кнопки назад в Редагуванні назви/категорії
@user_router.callback_query(UserAction.filter(F.action == Action.BACK))
async def go_back_edit_category(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == DishSettings.id_for_edit_name:
        await callback.answer('Кроків назад вже немає. Додайте назву страви або натисність "Відмінити"')
        return
    previous_state = None
    for step in DishSettings.__all_states__:
        if step.state == current_state:
            await state.set_state(previous_state)
            await callback.message.answer(f'{DishSettings.text[previous_state]}', reply_markup=get_cancle_btn(sizes=(2,)))
            await callback.message.delete()
            return
        previous_state = step

#Обробка кнопки Відмінити

@user_router.callback_query(UserAction.filter(F.action == Action.CANCLE))
async def cancle_btn(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("<strong>Ви відмінили останню дію</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))
    await state.clear()


##############################################################################
#Обробка кнопки Додаємо ще одну страву
@user_router.callback_query(UserAction.filter(F.action == Action.add_dish))
async def add_one_more_dish(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("<strong>Введіть назву страви:</strong>" , reply_markup=get_cancle_btn(sizes=(1,)))
    await callback.answer()
    await state.set_state(AddDish.name)

#Обробка кнопки Категорії страв 
@user_router.callback_query(UserAction.filter(F.action == Action.dish_list))
async def get_categories_btn(callback: types.CallbackQuery, state: FSMContext):
    async with session_maker() as session:
        media, reply_markup = await catalog(session, menu_name='dish_list')
        await state.clear()
        await callback.message.delete()
        await callback.message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)
        await callback.answer()

#Обробка кнопки Повернутись в головне меню
@user_router.callback_query(UserAction.filter(F.action == Action.main))
async def get_main_page(callback: types.CallbackQuery, state: FSMContext):
    async with session_maker() as session:
        media, reply_markup = await get_menu_content(session, level=0, menu_name='main')
        await state.clear()
        try:
            await callback.message.edit_media(media=media, reply_markup=reply_markup)
        except Exception as e:
            print(f"Failed to edit media: {e}")
            await callback.message.delete()
            await callback.message.answer_photo(photo=media.media, caption=media.caption, reply_markup=reply_markup)
        await callback.answer()

##################MENU##################

@user_router.callback_query(MenuCallBack.filter())
async def user_menu(callback: types.CallbackQuery, callback_data:MenuCallBack):
    async with session_maker() as session:
        
        media, reply_markup = await get_menu_content(
            session,
            level=callback_data.level,
            menu_name=callback_data.menu_name,
            category=callback_data.category,
            page=callback_data.page
        )
        await callback.message.edit_media(media=media, reply_markup=reply_markup)
        await callback.answer()

