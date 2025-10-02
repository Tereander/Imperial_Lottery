from functools import lru_cache
import psycopg
from typing import Optional, Tuple
import logging

import database


@lru_cache(maxsize=1000)
def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    conn, cursor = database.postgres_init()
    try:
        cursor.execute('SELECT is_admin FROM user_data WHERE user_id=%s', (user_id,))
        result: Optional[Tuple[bool]] = cursor.fetchone()
        return bool(result[0]) if result else False
    except psycopg.Error as e:
        logging.error(f"Ошибка БД при проверке админа (user_id={user_id}): {e}")
        return False
    finally:
        conn.close()


# Ручной сброс кэша (по команде /reset_admin_cache)
def clear_admin_cache():
    is_admin.cache_clear()

# clear_admin_cache()
