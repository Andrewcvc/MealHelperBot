import math
from sqlalchemy import select, update, delete

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload
from database.models import Banner, Category, Dish, User

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

async def orm_get_categories(session: AsyncSession):
    query = select(Category)
    result = await session.execute(query)
    return result.scalars().all()

async def orm_create_categories(session: AsyncSession, categories: list):
    query = select(Category)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Category(name=name) for name in categories]) 
    await session.commit()
    
############### Работа зі стравами ###############

async def orm_add_dish(session: AsyncSession, data: dict):
    obj = Dish(
        name=data["name"],
        category_id=int(data["category"]),
    )
    session.add(obj)
    await session.commit()


async def orm_get_dishes(session: AsyncSession, category_id):
    query = select(Dish).where(Dish.category_id == int(category_id))
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_dish(session: AsyncSession, dish_id: int):
    query = select(Dish).where(Dish.id == dish_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_update_dish(session: AsyncSession, dish_id: int, data):
    query = (
        update(Dish)
        .where(Dish.id == dish_id)
        .values(
            name=data["name"],
            category_id=int(data["category"]),
        )
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_dish(session: AsyncSession, dish_id: int):
    query = delete(Dish).where(Dish.id == dish_id)
    await session.execute(query)
    await session.commit()