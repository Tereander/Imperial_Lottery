import os
from typing import Dict, Any

import configparser
import logging

def load_config() -> configparser.ConfigParser:
    config_file_null = configparser.ConfigParser()
    config_path = os.path.join('config', 'config.ini')
    if not config_file_null.read(config_path, encoding='utf-8'):
        raise FileNotFoundError(f"Не удалось загрузить {config_path}!")
    return config_file_null

config_file = load_config()

try:
    # Параметры подключения к SQL базе данных
    sql_database: Dict[str, Any] = {
        'database': config_file['sql']['database'],
        'user': config_file['sql']['user'],
        'password': config_file['sql']['password'],
        'host': config_file['sql']['host'],
        'port': config_file['sql']['port'],
    }

    telegram = {
        'token': config_file['telegram']['token'],
        'admin_chat': -1002546605831,
    }
except KeyError as e:
    raise ValueError(f"В конфиге отсутствует ключ: {e}")


# template_path = os.path.join('tempates', 'template_phd.png')
# filename_reports = os.path.join('reports', 'participants_data.xlsx')
# if not os.path.exists(template_path):
#     raise FileNotFoundError(f"Шаблон {template_path} не найден!")


log_level: int = logging.INFO

master_id = 727403326

# callbacks
BROADCAST_CONFIRM_CALLBACK: str = "start_broadcast"
BROADCAST_CANCEL_CMD = '/cancel_broadcast'

price_pack_coupons = 10
start_gift_coin = 20

collection_type_list = [
    'Inquisition',
    'Master',
    'Demonic',
]
weights = {
    "common": 95,
    "uncommon": 4,
    "rare": 0.89,
    "epic": 0.1,
    "legendary": 0.01
}

color_prices = {
    "white": 1,
    "blue": 1,
    "puple": 5,
    "red": 10,
    "gold": 20
}

qty = {
    "common": 20,
    "uncommon": 15,
    "rare": 10,
    "epic": 4,
    "legendary": 1
}

template_paths = {
    "common": r"templates\template_common.png",
    "uncommon": r"templates\template_uncommon.png",
    "rare": r"templates\template_rare.png",
    "epic": r"templates\template_epic.png",
    "legendary": r"templates\template_legendary.png"
}
