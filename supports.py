import json
import logging
from typing import Tuple, Dict, Optional

import telebot
from telebot import TeleBot, types
from telebot.types import Message

import database
import dict_convert
import generators
import coupons
import configs


def process_promo_amount(message: Message, bot: TeleBot):
    try:
        amount = int(message.text)
        if not 1 <= amount <= 286:
            bot.send_message(message.chat.id, "❌ Сумма должна быть от 1 до 286!")
            return

        # Генерируем промокод
        promo_code = generators.generate_promo_code(amount)
        bot.send_message(
            message.chat.id,
            f"🎉 Ваш промокод на **{amount} монет**:\n\n`{promo_code}`\n\n"
            "Используйте его в боте через команду /promo!",
            parse_mode="Markdown"
        )

    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Введите число, например: 100")


def process_promo_code(message: Message, bot: TeleBot):
    user_id = message.from_user.id
    promo_code = message.text.strip().upper()

    # Проверяем валидность промокода
    is_valid, amount = generators.validate_promo_code(promo_code)
    if not is_valid:
        bot.send_message(message.chat.id, "❌ Неверный промокод!")
        return

    # Пытаемся начислить монеты
    success = coupons.add_coins_to_user(user_id, amount, promo_code)
    if success:
        bot.send_message(
            message.chat.id,
            f"🎉 Вам начислено **{amount}** монет!",
            parse_mode="Markdown")
    else:
        bot.send_message(
            message.chat.id,
            "⚠️ Промокод уже использован или произошла ошибка!",
            parse_mode="Markdown")

def converter_type_user_data(message: types.Message) -> Dict[str, Optional[str]]:
    """Конвертирует данные пользователя из message в словарь."""
    if not message or not message.from_user:
        return {}

    user = message.from_user
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "username": user.username,
        "language_code": user.language_code,
        "is_bot": user.is_bot,
        "is_premium": getattr(user, 'is_premium', None)  # Безопасное получение
    }

def info_message(user_id, message, bot):
    conn, cursor = database.postgres_init()

    try:
        cursor.execute(
            f"""SELECT user_data, opened_cases, title FROM user_data WHERE user_id={user_id}"""
        )
        user_list = cursor.fetchone()
        user_data, opened_cases, title = user_list
        print(type(user_data))
        # user_data = json.load(user_data)

        cursor.execute(
            f"""SELECT qty_coins FROM money WHERE user_id={user_id}"""
        )
        qty_coins = int(cursor.fetchone()[0])
    except (Exception, BaseException):
        bot.send_message(
            message.chat.id,
            'Ошибка загрузки данных, попробуйте позже'
        )
        return
    finally:
        conn.close()
        cursor.close()

    bot.send_message(
        message.chat.id,
        'Информация о пользователе:\n'
        '\n'
        f'Имя: <b>{user_data['full_name']}</b>\n'
        f'Титул: <b>{title}</b>\n'
        f'Баланс: <b>{qty_coins}</b>\n'
        f'Открыто кейсов: <b>{opened_cases}</b> шт.\n',
        parse_mode='html'
    )


def my_coupons(user_id, message, bot):
    conn, cursor = database.postgres_init()
    coupons_list = []

    try:
        cursor.execute("SELECT * FROM user_coupons WHERE user_id=%s", (user_id,))
        coupons_list = cursor.fetchall()
    except Exception as error:
        logging.error(f'Ошибка при получении списка купонов из БД: {error}')
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при загрузке ваших купонов")
        return
    finally:
        conn.close()

    if not coupons_list:
        bot.send_message(message.chat.id, "🎫 У вас пока нет купонов")
        return

    # Разбиваем список купонов на части по 50 штук
    chunk_size = 50
    coupons_chunks = [coupons_list[i:i + chunk_size]
                      for i in range(0, len(coupons_list), chunk_size)]

    total_chunks = len(coupons_chunks)

    for chunk_num, chunk in enumerate(coupons_chunks, 1):
        markup = types.InlineKeyboardMarkup(row_width=2)
        button_list = []

        for coupon in chunk:
            us_id, coupon_code, quantity, name, color = coupon
            smile = dict_convert.color_to_smile_convert.get(color, "🎟️")
            button = types.InlineKeyboardButton(
                f"{smile} {name}",
                callback_data=f'coupon_code {coupon_code}'
            )
            button_list.append(button)

        markup.add(*button_list)

        # Формируем текст сообщения
        if total_chunks > 1:
            header = f"🎫 Ваши купоны (часть {chunk_num} из {total_chunks})"
        else:
            header = "🎫 Ваши купоны"

        if chunk_num == 1 and len(coupons_list) > chunk_size:
            header += "\n\n📋 У вас много купонов! Они разделены на несколько сообщений для удобства."

        bot.send_message(message.chat.id, header, reply_markup=markup)