import logging
import os


def setup_logging(log_level: int = logging.DEBUG, log_dir: str = "logs",
                  log_file: str = "quiz_bot.log") -> None:
    """Настраивает глобальное логирование для всего приложения.

    Args:
        log_level: Уровень логирования (по умолчанию INFO)
        log_dir: Директория для логов (по умолчанию 'logs')
        log_file: Имя лог-файла (по умолчанию 'quiz_bot.log')
    """
    try:
        # Создаём папку для логов, если её нет
        os.makedirs(log_dir, exist_ok=True)

        # Полный путь к лог-файлу
        full_log_path = os.path.join(log_dir, log_file)

        # Настройка базовой конфигурации логирования
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(full_log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        logging.info("Логирование успешно настроено")

    except PermissionError as e:
        logging.error(f"Ошибка прав доступа при настройке логирования: {e}")
        raise
    except Exception as e:
        logging.error(f"Неожиданная ошибка при настройке логирования: {e}")
        raise
