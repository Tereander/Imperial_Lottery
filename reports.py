import os

import database

# Функция для обработки Excel файла
def process_excel_file(message, bot):
    try:
        # Проверяем, что сообщение содержит документ
        if message.document is None:
            bot.reply_to(message, "Пожалуйста, отправьте файл в формате Excel.")
            return

        # Получаем информацию о файле
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Сохраняем файл
        file_name = message.document.file_name
        save_path = os.path.join('downloads', file_name)

        with open(save_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.reply_to(message, f"Файл {file_name} успешно загружен. Обрабатываю...")

        # Парсим Excel и загружаем в базу данных
        database.parse_and_save_to_db(save_path, message, bot)

    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")