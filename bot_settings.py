import logging
import time

import requests
import telebot
from telebot import types
from telebot import TeleBot
from telebot.types import Message

import configs


def run_bot(bot):
    retry_delay = 1
    max_delay = 60

    while True:
        try:
            logging.info('Бот запущен')
            bot.polling(none_stop=True)

        except requests.exceptions.ReadTimeout as e:
            error_msg = "⚠️ Сервер не отвечает. Ждем 15 секунд и пробуем снова."
            logging.error(f"ReadTimeout: {e}")
            #supports.send_simple_message(bot, error_msg)
            time.sleep(15)

        except requests.exceptions.ConnectionError as e:
            error_msg = "🔌 Проблемы с подключением к интернету. Ждем 15 секунд и пробуем снова."
            logging.error(f"ConnectionError: {e}")
            #supports.send_simple_message(bot, error_msg)
            time.sleep(15)

        except Exception as short_error:
            error_msg = "❌ Неизвестная ошибка в работе бота. Ждем 10 секунд и пробуем перезапустить."
            logging.error(f"Other error: {short_error}")
            #supports.send_simple_message(bot, error_msg)
            time.sleep(10)

        # Exponential Backoff
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, max_delay)


def create_bot() -> telebot.TeleBot:
    """Создает экземпляр бота с обработкой ошибок."""
    try:
        return telebot.TeleBot(configs.telegram['token'])
    except KeyError:
        logging.critical("Токен бота не найден в конфиге!")
        raise
    except Exception as e:
        logging.critical(f"Ошибка создания бота: {e}")
        raise