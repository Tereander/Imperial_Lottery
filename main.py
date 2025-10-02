# Стандартные библиотеки
import time
import os
import datetime
from typing import Dict, List, Optional
import logging

# Локальные модули
import configs
import keyboards
import logs
import reports
import coupons
import supports
import database
import bot_settings


bot = bot_settings.create_bot()


@bot.message_handler(commands=["menu"])
def main_menu(message):
    user_id = message.from_user.id
    bot.send_message(
        message.chat.id,
        'Главное меню. Тут можно купить троны и открыть бустеры и многое другое.',
        reply_markup=keyboards.main_menu_keyboards(user_id)
    )
    return


@bot.message_handler(commands=["start"])
def start_menu(message):
    user_id = message.from_user.id
    user_data = supports.converter_type_user_data(message=message)

    # Сначала проверяем, есть ли пользователь в БД
    if not coupons.check_user_exists(user_id):
        # Если пользователя нет - начисляем стартовые монеты
        success = coupons.add_start_coins(user_id=user_id, amount=configs.start_gift_coin)
        if success:
            bot.send_message(
                message.chat.id,
                f'Добро пожаловать в бота имперской лотереи! Мы тебе рады. '
                f'В качестве подарка мы начислили тебе {configs.start_gift_coin} монет. '
                'Нажми /menu для продолжения.'
            )
        else:
            bot.send_message(
                message.chat.id,
                'Произошла ошибка при начислении стартовых монет. Пожалуйста, попробуйте позже.'
            )
    else:
        # Если пользователь уже есть - просто приветствуем без начисления
        bot.send_message(
            message.chat.id,
            'С возвращением в бота имперской лотереи! Нажми /menu для продолжения.'
        )

    # В любом случае обновляем данные пользователя
    logging.info(f"Сохранение/обновление данных пользователя {user_id} в БД")
    database.insert_user_data_in_bd(user_id=user_id, user_data=user_data)


# Обработчик inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    user_data = call.from_user

    if call.data == 'upload_cards':
        msg = bot.send_message(call.message.chat.id, "Пожалуйста, отправьте Excel файл с описанием карт.")
        bot.register_next_step_handler(msg, reports.process_excel_file, bot)

    if call.data == 'promo_generate':
        msg = bot.send_message(call.message.chat.id, "💰 Введите сумму для промокода (от 1 до 286):")
        bot.register_next_step_handler(msg, supports.process_promo_amount, bot)

    if call.data == 'open_coupons':

        if not coupons.coin_check(user_id, configs.price_pack_coupons):
            bot.send_message(call.message.chat.id, 'Ошибка! Не хватает Имперских трон для покупки!!')
            return

        coupons.open_buster(bot, call.message, user_id)

        qty_coin = coupons.qty_coin(user_id)
        bot.send_message(call.message.chat.id, f'ТВой баланс: {qty_coin} Имперских трон!\n',
                         reply_markup=keyboards.repeat_keyboards())
        return

    if call.data == 'promo':
        msg = bot.send_message(
            call.message.chat.id,
            "🔑 Введите промокод в формате **XXXX-XXXX-XXXX**:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, supports.process_promo_code, bot)

    if call.data == 'info':
        supports.info_message(user_id, call.message, bot)
        return

    if call.data == 'my_coupons':
        supports.my_coupons(user_id, call.message, bot)

    if 'coupon_code' in call.data:
        coupon_text = call.data
        coupon_list = coupon_text.split()
        coupon_code = coupon_list[1]
        coupons.get_coupon_info(coupon_code, bot, call.message, user_id)

    if 'activate' in call.data:
        coupon_text = call.data
        coupon_list = coupon_text.split()
        coupon_code = coupon_list[1]
        coupons.activate_coupon(coupon_code, bot, call.message, user_id, user_data)

    if 'sell' in call.data:
        coupon_text = call.data
        coupon_list = coupon_text.split()
        coupon_code = coupon_list[1]
        coupons.sell_coupon(coupon_code, bot, call.message, user_id, user_data)

if __name__ == '__main__':
    try:
        # Настройка логирования при запуске приложения
        logs.setup_logging(log_level=configs.log_level)
        bot_settings.run_bot(bot)
        # bot.polling(none_stop=True)
    except Exception as e:
        logging.critical(f"Критическая ошибка в основном цикле программы: {e}")
        #supports.send_simple_message(bot, "🔥 Критическая ошибка! Бот остановлен. Требуется вмешательство!")