from aiogram.utils.formatting import Bold, as_list, as_marked_section

categories = [
    "Перші страви🥣",
    "Гарніри🍝",
    "М'ясні страви🥩",
    "Салати/Овочі🥗",
    "Повноцінні страви🍲",
]

description_for_pages = {
    'main': '<strong>Ласкаво просимо до головного меню😊</strong>',
    'add_dish': '<strong>Введіть назву вашої страви:</strong>',
    'dish_list': '<strong>Виберіть категорію:</strong>',
    'menu_for_week': '<strong>Оберіть алгоритм генерації:</strong>',
    'dish_of_the_day': '<strong>Оберіть категорію з якої буде згенеровано страву:</strong>',
    'feedback': '<strong>Залиште відгук для покращення сервісу:</strong>',
}