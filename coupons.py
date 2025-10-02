import logging
import random
import traceback

import telebot
from telebot.types import InputMediaPhoto

import configs
import generators
import database
import images
import dict_convert
import keyboards
from dict_convert import smile_convert


logger = logging.getLogger(__name__)  # Лучше использовать именованный логгер

def coin_check(us_id, price_pack_coupons):
    conn, cursor = database.postgres_init()
    try:
        cursor.execute(
            f'SELECT qty_coins FROM money WHERE user_id=%s', (us_id,)
        )
        qty_coins = cursor.fetchone()
        coins = int(qty_coins[0])
        if coins < configs.price_pack_coupons:
            return False
        else:
            # Обновляем количество монет
            cursor.execute(
                'UPDATE money SET qty_coins = qty_coins - %s WHERE user_id = %s',
                (price_pack_coupons, us_id,)
            )
            conn.commit()
            return True
    except (Exception, BaseException):
        return False
    finally:
        conn.close()
        cursor.close()


def qty_coin(us_id):
    conn, cursor = database.postgres_init()
    try:
        cursor.execute(
            f'SELECT qty_coins FROM money WHERE user_id=%s', (us_id,)
        )
        qty_coins = cursor.fetchone()
        coins = int(qty_coins[0])
        return coins
    except (Exception, BaseException):
        return None
    finally:
        conn.close()
        cursor.close()


def add_coins_to_user(user_id: int, amount: int, promo_code: str) -> bool:
    """Добавляет монеты и записывает промокод в used"""
    conn, cursor = database.postgres_init()
    try:
        # Проверяем, не использовал ли пользователь этот промокод ранее
        cursor.execute(
            'SELECT 1 FROM promocode_used WHERE promocode = %s',
            (promo_code, )
        )
        if cursor.fetchone():
            return False  # Промокод уже использован

        # Начисляем монеты
        cursor.execute(
            'UPDATE money SET qty_coins = qty_coins + %s WHERE user_id = %s',
            (amount, user_id)
        )

        # Записываем промокод как использованный
        cursor.execute(
            'INSERT INTO promocode_used (user_id, promocode) VALUES (%s, %s)',
            (user_id, promo_code))

        conn.commit()
        return True

    except Exception as e:
        print(f"Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
        cursor.close()


def check_user_exists(user_id: int) -> bool:
    """Проверяет, существует ли пользователь в БД"""
    conn, cursor = database.postgres_init()
    try:
        cursor.execute('SELECT 1 FROM user_data WHERE user_id = %s LIMIT 1', (user_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def add_start_coins(user_id: int, amount: int) -> bool:
    """Начисляет стартовые монеты, создавая запись если её нет"""
    conn, cursor = database.postgres_init()
    try:
        # Используем INSERT ON CONFLICT для атомарной проверки и вставки
        cursor.execute('''
            INSERT INTO money (user_id, qty_coins) 
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO NOTHING
            RETURNING 1
        ''', (user_id, amount))

        # Если запись была добавлена (RETURNING 1 вернул результат)
        if cursor.fetchone():
            conn.commit()
            return True

        # Если запись уже существовала (ON CONFLICT DO NOTHING)
        conn.rollback()
        return False
    except Exception as e:
        logging.error(f"Ошибка при начислении стартовых монет: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def update_user_title(bot, user_id, chat_id):
    """Проверяет и обновляет титул пользователя, отправляет закрепленное сообщение"""
    conn, cursor = database.postgres_init()
    try:
        # Получаем текущие данные пользователя
        cursor.execute(
            'SELECT opened_cases, title FROM user_data WHERE user_id = %s',
            (user_id,)
        )
        user_data = cursor.fetchone()

        if not user_data:
            logging.error(f"User {user_id} not found in database")
            return

        opened_cases, current_title = user_data

        # Ищем подходящий титул (сортировка от большего к меньшему)
        new_title = None
        for threshold in sorted(dict_convert.CASE_TITLES.keys(), reverse=True):
            if opened_cases >= threshold:
                if dict_convert.CASE_TITLES[threshold]["title"] != current_title:
                    new_title = dict_convert.CASE_TITLES[threshold]
                break

        # Если нашли новый титул - обновляем
        if new_title:
            # Обновляем титул в БД
            cursor.execute(
                'UPDATE user_data SET title = %s WHERE user_id = %s',
                (new_title["title"], user_id)
            )
            conn.commit()

            # Формируем сообщение с описанием титула
            congrat_msg = (
                f"🎉 <b>Новый титул получен!</b>\n\n"
                f"🏆 <b>{new_title['title']}</b>\n"
                f"📜 <i>{new_title['description']}</i>\n\n"
                f"📊 Открыто кейсов: <code>{opened_cases}</code>\n"
                f"🔮 Следующий титул через: <code>{next_threshold(opened_cases)}</code>"
            )

            # Отправляем и закрепляем сообщение
            sent_msg = bot.send_message(
                chat_id,
                congrat_msg,
                parse_mode='HTML'
            )

    except Exception as e:
        logging.error(f"Error updating user title: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def next_threshold(current_count):
    """Возвращает сколько нужно до следующего титула"""
    thresholds = sorted(dict_convert.CASE_TITLES.keys())
    for threshold in thresholds:
        if current_count < threshold:
            return threshold - current_count
    return "∞ (максимум)"


def open_buster(bot, message, user_id):
    """
    Открывает бурстер с купонами для пользователя.

    Генерирует купоны, сохраняет их в БД, создает графические представления купонов,
    отправляет пользователю информацию о полученных купонах и их изображения.

    Args:
        bot: Объект бота для отправки сообщений
        message: Объект сообщения от пользователя
        user_id: ID пользователя, открывающего бурстер

    Returns:
        None
    """
    # Генерируем купоны
    coupons = generators.generate_coupons(qty_coupons=5)
    logger.debug(f"Сгенерированы купоны: {coupons}")

    # Инициализируем подключение к БД
    conn, cursor = database.postgres_init()
    coupons_list = []  # Пути к изображениям купонов
    coupon_details = []  # Информация о купонах для сообщения

    try:
        # Увеличиваем счетчик открытых кейсов
        logger.debug(f"Обновляем счетчик открытых кейсов для user_id={user_id}")
        cursor.execute(
            'UPDATE user_data SET opened_cases = opened_cases + 1 WHERE user_id = %s RETURNING opened_cases',
            (user_id,)
        )
        new_case_count = cursor.fetchone()[0]
        conn.commit()
        logger.debug(f"Новое количество открытых кейсов: {new_case_count}")

        # Проверяем и обновляем титул пользователя
        logger.debug("Проверяем обновление титула пользователя")
        update_user_title(bot, user_id, message.chat.id)

        # Обрабатываем каждый сгенерированный купон
        for coupon in coupons:
            color = dict_convert.color_convert[coupon['rarity']]
            collection_type = random.choice(configs.collection_type_list)
            id_for_search = f'{collection_type}_{color}_{coupon["number"]}'

            logger.debug(f"Ищем купон в БД: id={id_for_search}")

            cursor.execute('SELECT * FROM coupons WHERE id=%s', (id_for_search,))
            coupon_data = cursor.fetchone()

            if not coupon_data:
                logging.warning(f"Купон не найден в БД: {id_for_search}")
                continue  # Пропускаем, если купон не найден

            id_coupons, number, name, color, effect, description, collection = coupon_data
            coupons_list.append(fr"downloads_coupons\{id_coupons}.png")
            logger.debug(f"Добавлен купон {id_coupons} в список для обработки")

            # Формируем строку с информацией о купоне
            rarity_emoji = dict_convert.smile_convert.get(coupon['rarity'], '❓')
            coupon_details.append(
                f"{rarity_emoji} <b>{name}</b> (№{number}, {collection_type})\n"
            )

            # Генерируем картинку купона
            try:
                logger.debug(f"Генерируем изображение для купона {id_coupons}")
                images.create_coupon(
                    rarity=coupon['rarity'],
                    title=name,
                    description=description,
                    effect=effect,
                    coupon_number=number,
                    coupon_code=id_coupons,
                    collection_type=collection_type,
                    output_path=fr"downloads_coupons\{id_coupons}.png",
                )
                logger.debug(f"Изображение купона {id_coupons} успешно создано")
            except Exception as e:
                logger.error(f'Ошибка генерации карточки купона {id_coupons}: {e}')
                logger.debug(f"Трассировка ошибки: {traceback.format_exc()}")

            # Сохраняем купон в БД за пользователем
            try:
                logger.debug(f"Сохраняем купон {id_coupons} для пользователя {user_id}")
                database.save_info_coupon(user_id, id_coupons, name, color)
            except Exception as e:
                logger.error(
                    f"Ошибка сохранения купона {id_coupons} для пользователя {user_id}: {e}")

        # Формируем общее сообщение с информацией о купонах
        rarity_emojis = " ".join(
            [dict_convert.smile_convert.get(coupon['rarity'], '❓')
             for coupon in coupons]
        )
        logger.debug(f"Сформированы эмодзи редкостей: {rarity_emojis}")

        message_text = (
                f"📊 <b>Содержимое пака:</b> {rarity_emojis}\n\n"
                f"<b>Полученные купоны:</b>\n"
                + "\n".join(coupon_details)
        )
        logger.debug(f"Текст сообщения для пользователя: {message_text}")

        # Отправляем сообщение с описанием купонов
        try:
            logger.debug("Отправляем текстовое сообщение с описанием купонов")
            bot.send_message(
                message.chat.id,
                message_text,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка отправки текстового сообщения: {e}")

        # Отправляем картинки медиагруппой
        if coupons_list:
            media_group = []
            logger.debug(f"Подготавливаем медиагруппу из {len(coupons_list)} изображений")

            for path in coupons_list:
                try:
                    logger.debug(f"Читаем файл изображения: {path}")
                    with open(path, 'rb') as photo:
                        photo_data = photo.read()
                    media_group.append(InputMediaPhoto(photo_data))
                except Exception as e:
                    logger.error(f"Ошибка загрузки картинки {path}: {e}")
                    logger.debug(f"Трассировка ошибки: {traceback.format_exc()}")

            if media_group:
                try:
                    logger.debug("Отправляем медиагруппу с изображениями купонов")
                    bot.send_media_group(message.chat.id, media_group)
                except Exception as e:
                    logger.error(f"Ошибка отправки медиагруппы: {e}")

    except Exception as e:
        logger.error(f"Критическая ошибка в open_buster: {e}")
        logger.debug(f"Трассировка ошибки: {traceback.format_exc()}")
        conn.rollback()
    finally:
        logger.debug("Закрываем соединение с БД")
        cursor.close()
        conn.close()


def get_coupon_info(coupon_code, bot, message, user_id):
    conn, cursor = database.postgres_init()
    try:
        cursor.execute('SELECT * FROM coupons WHERE id = %s', (coupon_code,))
        coupon_data = cursor.fetchone()
        coupon_code, number, name, color, effect, description, collection = coupon_data
        smile = dict_convert.color_to_smile_convert[color]

        cursor.execute(
            'SELECT quantity FROM user_coupons WHERE coupon_code = %s AND user_id = %s',
            (coupon_code, user_id)
        )
        quantity = int(cursor.fetchone()[0])

        bot.send_photo(message.chat.id, open(rf'downloads_coupons\{coupon_code}.png', 'rb'))
        bot.send_message(
            message.chat.id,
            f'{smile} Купон № {number}\n'
            f'Коллекция: {collection}\n'
            f'\n'
            f'{name}\n'
            f'\n'
            f'{effect}\n'
            f'Количество: {quantity} шт.',
            reply_markup=keyboards.my_coupons_data_keyboards(coupon_code)
        )

    except Exception as e:
        logging.error(f"Ошибка при получении информации о купоне: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def activate_coupon(coupon_code, bot, message, user_id, user_data):
    conn, cursor = database.postgres_init()
    try:
        # Получаем данные о купоне
        cursor.execute(
            'SELECT quantity, name, color FROM user_coupons '
            'WHERE coupon_code = %s AND user_id = %s',
            (coupon_code, user_id)
        )
        result = cursor.fetchone()

        if not result:
            bot.send_message(message.chat.id, "❌ Купон не найден или уже использован")
            return

        quantity, name, color = result
        quantity = int(quantity)

        # Обновляем количество купонов или удаляем запись
        if quantity > 1:
            cursor.execute(
                'UPDATE user_coupons SET quantity = quantity - 1 WHERE coupon_code = %s AND user_id = %s',
                (coupon_code, user_id)
            )
        else:
            cursor.execute(
                'DELETE FROM user_coupons WHERE coupon_code = %s AND user_id = %s',
                (coupon_code, user_id)
            )

        # Фиксируем изменения в БД
        conn.commit()

        # Сообщение пользователю
        bot.send_message(
            message.chat.id,
            f"✅ Купон активирован! Мастер игры уведомлен. Вы можете использовать бонус"
        )
        smile = dict_convert.color_to_smile_convert[color]

        # Уведомление мастера
        bot.send_message(
            configs.master_id,
            f"🎫 Активирован купон:\n"
            f"• Название: {smile} {name}\n"
            f"• Код: {coupon_code}\n"
            f"• Пользователь: {user_data.full_name}",
            parse_mode='html'
        )

    except Exception as e:
        conn.rollback()
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при активации купона")
        print(f"Error activating coupon: {e}")


def sell_coupon(coupon_code, bot, message, user_id, user_data):
    conn, cursor = database.postgres_init()
    try:
        # Получаем данные о купоне
        cursor.execute(
            'SELECT quantity, name, color FROM user_coupons WHERE coupon_code = %s AND user_id = %s',
            (coupon_code, user_id)
        )
        result = cursor.fetchone()

        if not result:
            bot.send_message(message.chat.id, "❌ Купон не найден или уже использован")
            return

        quantity, name, color = result
        quantity = int(quantity)

        # Приводим цвет к нижнему регистру для сравнения
        color_lower = color.lower()

        if color_lower not in configs.color_prices:
            bot.send_message(message.chat.id, f"❌ Неизвестный цвет купона: {color}")
            return

        price = configs.color_prices[color_lower]

        # Обновляем количество купонов или удаляем запись
        if quantity > 1:
            cursor.execute(
                'UPDATE user_coupons SET quantity = quantity - 1 WHERE coupon_code = %s AND user_id = %s',
                (coupon_code, user_id)
            )
        else:
            cursor.execute(
                'DELETE FROM user_coupons WHERE coupon_code = %s AND user_id = %s',
                (coupon_code, user_id)
            )

        # Начисляем деньги пользователю
        # Сначала проверяем, есть ли запись о деньгах пользователя
        cursor.execute(
            'SELECT qty_coins FROM money WHERE user_id = %s',
            (user_id,)
        )
        money_result = cursor.fetchone()

        if money_result:
            # Обновляем существующую запись
            cursor.execute(
                'UPDATE money SET qty_coins = qty_coins + %s WHERE user_id = %s',
                (price, user_id)
            )
            new_balance = money_result[0] + price
        else:
            # Создаем новую запись
            cursor.execute(
                'INSERT INTO money (user_id, qty_coins) VALUES (%s, %s)',
                (user_id, price)
            )
            new_balance = price

        # Сообщение пользователю
        bot.send_message(
            message.chat.id,
            f"✅ Купон '{name}' ({color}) продан за {price} монет.\n"
            f"💰 Твой баланс: {new_balance} монет"
        )

        # Фиксируем изменения в БД
        conn.commit()

    except Exception as e:
        conn.rollback()
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при продаже купона")
        print(f"Error selling coupon: {e}")
