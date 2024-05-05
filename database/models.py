from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, BigInteger, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase): 
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now()) 
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now()) 
    
class Banner(Base):
    __tablename__= 'banner'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(15), unique=True)
    image: Mapped[str] = mapped_column(String(150), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
class Category(Base):
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    
class Dish(Base):
    __tablename__ = 'dish'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    # description: Mapped[str] = mapped_column(Text)
    # price: Mapped[float] = mapped_column(Numeric(5,2), nullable=False)
    # image: Mapped[str] = mapped_column(String(150))
    category_id: Mapped[int] = mapped_column(ForeignKey('category.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    
    user: Mapped['User'] = relationship('User', back_populates='dishes')    
    category: Mapped['Category'] = relationship(backref='dish')

class DishOfTheDay(Base):
    __tablename__ = 'dish_of_the_day'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dish_id: Mapped[int] = mapped_column(Integer, ForeignKey('dish.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)

    dish: Mapped['Dish'] = relationship('Dish', backref='dish_of_the_day')
    user: Mapped['User'] = relationship('User', backref='dish_of_the_day')

class DishOfTheWeek(Base):
    __tablename__ = 'dish_of_the_week'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dish_id: Mapped[int] = mapped_column(Integer, ForeignKey('dish.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)

    # Relationships
    dish: Mapped['Dish'] = relationship('Dish', backref='dish_of_the_week')
    user: Mapped['User'] = relationship('User', backref='dish_of_the_week')

class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True) # Telegram user_id
    first_name: Mapped[str] = mapped_column(String(150), nullable=True)
    last_name: Mapped[str]  = mapped_column(String(150), nullable=True)
    user_name: Mapped[str]  = mapped_column(String(150), nullable=True)
    phone: Mapped[str]  = mapped_column(String(13), nullable=True)
    
    dishes: Mapped['Dish'] = relationship("Dish", order_by=Dish.id, back_populates="user")


class Menu(Base):
    __tablename__ = 'menu'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    dish_id: Mapped[int] = mapped_column(ForeignKey('dish.id', ondelete='CASCADE'), nullable=False)
    quantity: Mapped[int]

    user: Mapped['User'] = relationship(backref='menu')
    dish: Mapped['Dish'] = relationship(backref='menu')

class PickedDishes(Base):
    __tablename__ = 'picked_dishes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    dish_id: Mapped[int] = mapped_column(Integer, ForeignKey('dish.id', ondelete='CASCADE'), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey('category.id', ondelete='CASCADE'), nullable=False)
    picked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped['User'] = relationship('User', backref='picked_dishes')
    dish: Mapped['Dish'] = relationship('Dish', backref='picked_dishes')
    category: Mapped['Category'] = relationship('Category', backref='picked_dishes')
    
class UserPreference(Base):
    __tablename__ = 'user_preference'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.user_id'), unique=True)
    preferences: Mapped[dict] = mapped_column(JSONB) # This column will store category and dish count preferences as JSON


