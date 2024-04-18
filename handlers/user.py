import json
from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command, or_f, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputMediaPhoto

from database.engine import session_maker
from handlers.menu_processing import AddDish, DishSettings, catalog, get_menu_content
from keyboards.inline import Action, MenuCallBack, UserAction, get_callback_btns, get_cancle_btn, get_dish_list_btns, get_edit_btns, get_empty_list_btns, get_user_added_btns

from database.orm_query import orm_add_dish, orm_add_user, orm_delete_dish, orm_get_categories, orm_get_dish, orm_get_dishes, orm_update_dish




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
        await callback.message.edit_media(media=media, reply_markup=reply_markup)
        await state.set_state(AddDish.name)
        await callback.answer()
        

async def go_back(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == AddDish.name:
        await callback.answer('Кроків назад вже немає. Додайте назву страви або натисність "Відмінити"')
        return
    previous_state = None
    for step in AddDish.__all_states__:
        if step.state == current_state:
            await state.set_state(previous_state)
            await callback.message.answer(f'Ви повернулись на крок назад. \n{AddDish.text[previous_state]}')
            await callback.message.delete()
            return
        previous_state = step

@user_router.message(AddDish.name, F.text)
async def add_dish_name(message: types.Message, state: FSMContext):
    async with session_maker() as session:
        if len(message.text) <= 3:
            await message.answer("Назва страви повинна бути від 3 символів.\n Введіть назву товару повторно:")
            return
        await state.update_data(name=message.text)
            
        categories = await orm_get_categories(session)
        btns = {category.name: str(category.id) for category in categories}
        btns['Назад'] = Action.BACK
        btns['Повернутись в головне меню🏠'] = UserAction(action=Action.main).pack()
        await message.answer('<strong>Оберіть категорію для вашої страви:</strong>', reply_markup=get_callback_btns(btns=btns))
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
        elif int(callback.data) in [category.id for category in await orm_get_categories(session)]:
            await callback.answer()
            await state.update_data(category=callback.data)
        else:
            await callback.answer('<strong>Виберіть категорію зі списку</strong>', show_alert=True)
            return
        
        data = await state.get_data() # отримуємо дані зі стейту
                
        await orm_add_dish(session, user_id=user_id, data=data)
        await callback.message.delete()
        await callback.message.answer('<strong>Страву додано</strong>', reply_markup=get_user_added_btns(sizes=(2,)))
        await callback.answer()
        await state.clear()


@user_router.message(AddDish.category, F.text)
async def delete_user_message(message: types.Message):
    await message.delete()
    await message.answer('<strong>Виберіть категорію зі списку вище</strong>')



##################*DISH LIST PAGE##################


@user_router.callback_query(F.data.startswith('category_'))
async def starring_at_dish(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    category_id = callback.data.split('_')[-1]
    
    async with session_maker() as session:
        await callback.message.delete()
        categories = await orm_get_categories(session)
        for category in categories:
            if category.id == int(callback.data.split('_')[-1]):
                category_name = category.name
        await callback.message.answer(f'<strong>Ось список страв з категорії\n"<b>{category_name}:</b>"</strong>')
        await state.update_data(category_id=category_id)
        dishes = await orm_get_dishes(session, user_id=user_id, category_id=category_id)
        if not dishes:
            await callback.message.answer("В цій категорії поки що немає страв", reply_markup=get_empty_list_btns(sizes=(2,)))
        else:
            for i, dish in enumerate(dishes):
                await callback.message.answer(f"{i+1}) {dish.name}")
            await callback.message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))
        await callback.answer()


############*Обробка кнопок################


##################*DELETE DISH BTN FSM##################
#Обробка кнопки Видалити страву
@user_router.callback_query(UserAction.filter(F.action==Action.DELETE))
async def delete_dish(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("<strong>Введіть номер страви, яку ви хочете видалити</strong>", reply_markup=get_cancle_btn(sizes=(1,)))
    await callback.answer()
    await state.set_state(DishSettings.id_for_delete)

### Мій Старий Варіант Видалення Страви
# @user_router.message(DishSettings.id_for_delete, F.text)   
# async def delete_dish_by_id(message: types.Message, state: FSMContext):
#     user_id = message.from_user.id
#     async with session_maker() as session:
#         user_data = await state.get_data()
#         category_id = user_data.get('category_id')
#         dishes = await orm_get_dishes(session, user_id=user_id, category_id=category_id)
        
#         for i, dish in enumerate(dishes):
#             if message.text == str(i+1):
#                 await orm_delete_dish(session, user_id=user_id, dish_id=dish.id)
#                 dishes = await orm_get_dishes(session, user_id=user_id, category_id=category_id)
#                 await message.answer(f"<strong>Страву '{dish.name}' видалено!\nОсь оновлений список</strong>")
#                 for i, dish in enumerate(dishes):
#                     await message.answer(f"<strong>{i+1}) {dish.name}</strong>")
#                 break
#         else:
#             await message.answer("<strong>Введіть коректний номер страви</strong>")
#         await message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))

@user_router.message(DishSettings.id_for_delete, F.text)
async def delete_dish_by_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with session_maker() as session:
        user_data = await state.get_data()
        categotry_id = user_data.get('category_id')
        dishes = await orm_get_dishes(session, user_id=user_id, category_id=categotry_id)
        
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
    await callback.message.delete()
    await callback.message.answer("<strong>Що саме ви хочете змінити:</strong>", reply_markup=get_edit_btns(sizes=(2,)))

#Обробка кнопки Змінити назву

@user_router.callback_query(UserAction.filter(F.action == Action.edit_name))
async def edit_dish_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("<strong>Введіть номер страви, назву якої ви хочете відредагувати</strong>", reply_markup=get_cancle_btn(sizes=(1,)))
    await callback.answer()
    await state.set_state(DishSettings.id_for_edit_name)


@user_router.message(DishSettings.id_for_edit_name, F.text)
async def edit_dish_by_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    dish_index = message.text.isdigit() and int(message.text) - 1
    
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


# Мій старий варіант
# @user_router.message(DishSettings.edit_name, F.text)
# async def edit_dish_name(message: types.Message, state: FSMContext):
#     user_data = await state.get_data()
#     category_id = user_data.get('category_id')
# await state.update_data(category=int(category_id))
#     dish_id = user_data.get('dish_id_for_edit')
    
#     async with session_maker() as session:
#         if AddDish.dish_edit:
#             await state.update_data(name=AddDish.dish_edit.name)
#         else:
#             if len(message.text) <= 3:
#                 await message.answer("Назва страви повинна бути від 3 символів.\n Введіть назву товару повторно:")
#                 return
#         await state.update_data(name=message.text)
#         await state.update_data(category=int(category_id))
#         data = await state.get_data()
#         try:
#             if AddDish.dish_edit and 'category' in data:
#                 await orm_update_dish(session, AddDish.dish_edit.id, data)
#                 dishes = await orm_get_dishes(session, category_id=category_id)
#                 await message.answer(f"<strong>Назву успішно змінено!\nОсь оновлений список:</strong>")
#                 for i, dish in enumerate(dishes):
#                     await message.answer(f"<strong>{i+1}) {dish.name}</strong>")
#             await message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))
#         except Exception as e:
#             await message.answer(f"<strong>Помилка: \n{str(e)}</strong>")
#             await message.answer("<strong>Меню:</strong>", reply_markup=get_dish_list_btns(sizes=(2,)))
#             await state.clear()

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
    category_id = dish_data.get('category_id')
    print(f"Received dish data: {dish_data}")
    
    async with session_maker() as session:
        categories = await orm_get_categories(session)
        category_ids = [category.id for category in categories]
        print(f"Category IDs: {category_ids} callback {callback.data}")
        
        if callback.data == UserAction(action=Action.main).pack():
            await get_main_page(callback, state)
        elif int(callback.data) in category_ids:
            await callback.answer()
            await state.update_data(name=dish_name)
            await state.update_data(category=callback.data)
            print(f"Received disddsdssh data: {dish_data}")
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
            print(f"Error updating category: {e}")
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
        await callback.message.delete()
        await callback.message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)
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
            page=callback_data.page,
        )
        await callback.message.edit_media(media=media, reply_markup=reply_markup)
        await callback.answer()

