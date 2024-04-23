import json
import math
import traceback

import random
from sqlalchemy import func, select, update, delete, cast, Date

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload
from database.models import Banner, Category, Dish, DishOfTheDay, DishOfTheWeek, User, UserPreference
from sqlalchemy.exc import SQLAlchemyError

############### Работа з баннерами ###############

async def orm_add_banner_description(session: AsyncSession, data: dict):
    query = select(Banner)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Banner(name=name, description=description) for name, description in data.items()]) 
    await session.commit()
    
async def orm_change_banner_image(session: AsyncSession, name: str, image: str):
    query = update(Banner).where(Banner.name == name).values(image=image)
    await session.execute(query)
    await session.commit()
    
async def orm_get_banner(session: AsyncSession, page: str):
    query = select(Banner).where(Banner.name == page)
    result = await session.execute(query)
    return result.scalar()

async def orm_get_info_pages(session: AsyncSession):
    query = select(Banner)
    result = await session.execute(query)
    return result.scalars().all()

############### Работа з користувачами ###############

async def orm_add_user(
    session: AsyncSession,
    user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    user_name: str | None = None,
    phone: str | None = None,
):
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    if result.first() is None:
        session.add(
            User(user_id=user_id, first_name=first_name, last_name=last_name, user_name=user_name, phone=phone)
        )
        await session.commit()
        
############### Работа с категоріями ###############
async def orm_get_categories(session: AsyncSession, category_ids=None):
    if category_ids:
        query = select(Category).where(Category.id.in_(category_ids))
    else:
        query = select(Category)
    result = await session.execute(query)
    return result.scalars().all()

async def orm_get_categories_by_ids(session: AsyncSession, category_ids: list):
    try:
        result = await session.execute(
            select(Category).where(Category.id.in_(category_ids))
        )
        return result.scalars().all()
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

async def orm_create_categories(session: AsyncSession, categories: list):
    query = select(Category)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Category(name=name) for name in categories]) 
    await session.commit()
    
############### Работа зі стравами ###############

async def orm_add_dish(session: AsyncSession, user_id: int, data: dict):
    obj = Dish(
        name=data["name"],
        category_id=int(data["category"]),
        user_id=user_id,
    )
    session.add(obj)
    await session.commit()


async def orm_get_dishes(session: AsyncSession, user_id: int, category_id):
    query = select(Dish).where(Dish.category_id == int(category_id), Dish.user_id == user_id)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_dish(session: AsyncSession, user_id: int, dish_id: int):
    query = select(Dish).where(Dish.id == dish_id, Dish.user_id == user_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_update_dish(session: AsyncSession, user_id: int, dish_id: int, data):
    query = (
        update(Dish)
        .where(Dish.id == dish_id, Dish.user_id == user_id)
        .values(
            name=data["name"],
            category_id=int(data["category"]),
        )
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_dish(session: AsyncSession, user_id: int, dish_id: int):
    query = delete(Dish).where(Dish.id == dish_id, Dish.user_id == user_id)
    await session.execute(query)
    await session.commit()

############### Работа зі стравами дня ###############

async def add_random_dish_of_the_day(session: AsyncSession, user_id: int, category_id: int):
    query = select(Dish).where(Dish.category_id == category_id)
    result = await session.execute(query)
    dishes = result.scalars().all()
    
    if dishes:
        chosen_dish = random.choice(dishes)
        obj = DishOfTheDay(dish_id=chosen_dish.id, user_id=user_id)
        session.add(obj)
        try:
            await session.commit()
            return chosen_dish
        except Exception as e:
            print("Failed to commit to database:", e)
            traceback.print_exc()
            await session.rollback()  # Roll back in case of error
            return None
    return None


async def get_dishes_of_the_day(session: AsyncSession, user_id: int):


    query = select(DishOfTheDay).options(
        joinedload(DishOfTheDay.dish).joinedload(Dish.category)
    ).where(
        DishOfTheDay.user_id == user_id
    )
    result = await session.execute(query)
    dishes = result.scalars().all()
    return dishes

async def clear_dishes_of_the_day(session: AsyncSession, user_id: int):
    await session.execute(delete(DishOfTheDay).where(DishOfTheDay.user_id == user_id))
    await session.commit()

###############* Работа з меню на тиждень ###############

async def orm_get_random_dishes(session: AsyncSession, category_id: int, count: int):
    query = select(Dish).options(joinedload(Dish.category)).where(Dish.category_id == category_id).order_by(func.random()).limit(count)
    result = await session.execute(query)
    return result.scalars().all()


async def add_dishes_of_the_week(session: AsyncSession, user_id: int, preferences: dict):
    for category_id, count in preferences.items():
        dishes = await orm_get_random_dishes(session, category_id, count)
        for dish in dishes:
            obj = DishOfTheWeek(dish_id=dish.id, user_id=user_id)
            session.add(obj)
    try:
        await session.commit()
    except Exception as e:
        print("Failed to commit to database:", e)
        traceback.print_exc()
        await session.rollback()


async def get_dishes_of_the_week(session: AsyncSession, user_id: int):
    query = select(DishOfTheWeek).options(
        joinedload(DishOfTheWeek.dish).joinedload(Dish.category)
    ).where(
        DishOfTheWeek.user_id == user_id
    )
    result = await session.execute(query)
    return result.scalars().all()


async def clear_dishes_of_the_week(session: AsyncSession, user_id: int):
    await session.execute(delete(DishOfTheWeek).where(DishOfTheWeek.user_id == user_id))
    await session.commit()


async def orm_update_user_preferences(session: AsyncSession, user_id: int, preferences: dict):
    try:
        existing_prefs = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        user_prefs = existing_prefs.scalars().first()

        if user_prefs:
            current_preferences = json.loads(user_prefs.preferences) if user_prefs.preferences else {}
            # Update the existing preferences with the new values or add them if they don't exist
            for category_id, count in preferences.items():
                current_preferences[str(category_id)] = count
            user_prefs.preferences = json.dumps(current_preferences)
        else:
            # Create a new preferences record if it doesn't exist
            new_prefs = UserPreference(user_id=user_id, preferences=json.dumps(preferences))
            session.add(new_prefs)

        await session.commit()
        return True
    except SQLAlchemyError as e:
        print(f"Failed to update or create preferences: {e}")
        await session.rollback()
        return False


async def orm_get_user_preferences(session: AsyncSession, user_id: int):
    try:
        existing_prefs = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        user_prefs = existing_prefs.scalars().first()
        return json.loads(user_prefs.preferences) if user_prefs and user_prefs.preferences else {}
    except Exception as e:
        print(f"Error retrieving preferences: {e}")
        return {}


async def orm_clear_user_preferences(session: AsyncSession, user_id: int):
    try:
        await session.execute(
            delete(UserPreference).where(UserPreference.user_id == user_id)
        )
        await session.commit()
        return True
    except SQLAlchemyError as e:
        print(f"Failed to clear user preferences: {e}")
        await session.rollback()
        return False

