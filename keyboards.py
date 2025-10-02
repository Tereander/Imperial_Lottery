from telebot import types

import admins

def main_menu_keyboards(us_id):

    markup = types.InlineKeyboardMarkup(row_width=2)
    button = types.InlineKeyboardButton("Купить купоны", callback_data='open_coupons')
    button2 = types.InlineKeyboardButton("Мои купоны", callback_data='my_coupons')
    button3 = types.InlineKeyboardButton("Активировать промокод", callback_data='promo')
    button5 = types.InlineKeyboardButton("Информация", callback_data='info')

    button_admin_1 = types.InlineKeyboardButton("Загрузить описание карт", callback_data='upload_cards')
    button_admin_2 = types.InlineKeyboardButton("Генерация промокодов", callback_data='promo_generate')

    markup.add(button, button2)
    markup.add(button3, button5)

    if admins.is_admin(us_id):
        markup.add(button_admin_1, button_admin_2)

    return markup


def repeat_keyboards():
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(
        "Открыть еще одну пачку купонов",
        callback_data='open_coupons'
    )
    markup.add(button)

    return markup


def my_coupons_data_keyboards(coupon_code):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Назад к списку купонов",callback_data='my_coupons')
    button2 = types.InlineKeyboardButton("Активировать купон", callback_data=f'activate {coupon_code}')
    button1 = types.InlineKeyboardButton("Продать купон", callback_data=f'sell {coupon_code}')

    markup.add(button2, button1)
    markup.add(button)

    return markup