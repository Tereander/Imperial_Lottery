import random

import configs

def generate_coupons(qty_coupons):

    # Создаем копии словарей для работы
    available = configs.qty.copy()
    weights_list = list(configs.weights.items())

    coupons = []

    # Генерируем 5 купонов
    for _ in range(qty_coupons):
        # Если это последний купон и еще нет uncommon или выше, форсируем выбор
        if len(coupons) == qty_coupons-1 and not any(c['rarity'] != 'common' for c in coupons):
            # Выбираем только из uncommon или выше
            forced_weights = {k: v for k, v in configs.weights.items() if k != 'common'}
            # Нормализуем веса
            total = sum(forced_weights.values())
            normalized_weights = {k: v / total for k, v in forced_weights.items()}

            # Выбираем редкость
            rarity = random.choices(
                list(normalized_weights.keys()),
                weights=list(normalized_weights.values()),
                k=1
            )[0]
        else:
            # Обычный выбор редкости
            rarity = random.choices(
                list(configs.weights.keys()),
                weights=list(configs.weights.values()),
                k=1
            )[0]

        # Проверяем, есть ли еще купоны такой редкости
        if available[rarity] <= 0:
            # Если нет, пробуем снова (можно оптимизировать)
            continue

        # Генерируем номер купона
        coupon_number = random.randint(1, configs.qty[rarity]+1)

        # Добавляем купон в результат
        coupons.append({
            "rarity": rarity,
            "number": coupon_number
        })

        # Уменьшаем количество доступных купонов этой редкости
        available[rarity] -= 1

    return coupons


import random
import string


def generate_promo_code(coin_amount: int) -> str:
    """
    Генерирует промокод с заданной суммой вознаграждения.

    Формат промокода: "XXXX-XXXX-XXYZ", где:
    - XXXX-XXXX — первые две части (условия: сумма=25, произведение кратно 10).
    - XXYZ — третья часть:
      - XX — случайные символы.
      - Y — буква, кодирующая десятки суммы (A=10, B=20, ..., Z=260).
      - Z — буква, кодирующая единицы суммы (A=1, B=2, ..., Z=26).

    Args:
        coin_amount (int): Сумма валюты для начисления (должна быть в диапазоне 1-286).

    Returns:
        str: Промокод в формате "XXXX-XXXX-XXYZ".
    """
    if not 1 <= coin_amount <= 286:
        raise ValueError("Сумма должна быть от 1 до 286")

    # Генерация первой части (сумма = 25)
    part1 = ""
    while True:
        part1 = ''.join(random.choices(string.digits + string.ascii_uppercase, k=4))
        total = sum(int(c) if c.isdigit() else (ord(c) - ord('A') + 1) for c in part1)
        if total == 25:
            break

    # Генерация второй части (произведение кратно 10)
    part2 = ""
    while True:
        part2 = ''.join(random.choices(string.digits + string.ascii_uppercase, k=4))
        product = 1
        has_two_or_five = False
        for c in part2:
            num = int(c) if c.isdigit() else (ord(c) - ord('A') + 1)
            product *= num
            if num in (2, 5):
                has_two_or_five = True
        if product % 10 == 0 and has_two_or_five:
            break

    # Генерация третьей части (первые 2 символа — случайные, последние 2 — сумма)
    tens = (coin_amount // 10) - 1  # A=10, B=20, ...
    units = (coin_amount % 10) - 1  # A=1, B=2, ...
    if tens < 0:
        tens = 25  # Если сумма <10, десятки = Z (0), но лучше избегать этого случая
    y_char = chr(ord('A') + tens)
    z_char = chr(ord('A') + units)

    part3 = ''.join(random.choices(string.ascii_uppercase, k=2)) + y_char + z_char

    return f"{part1}-{part2}-{part3}"


def validate_promo_code(promo_code: str) -> tuple[bool, int]:
    """
    Проверяет валидность промокода и извлекает сумму вознаграждения.

    Args:
        promo_code (str): Промокод в формате "XXXX-XXXX-XXYZ".

    Returns:
        tuple[bool, int]: (True, сумма) если промокод валиден, иначе (False, 0).
    """
    # Проверка формата
    if len(promo_code) != 14 or promo_code[4] != '-' or promo_code[9] != '-':
        return False, 0

    parts = promo_code.split('-')
    if len(parts) != 3:
        return False, 0

    part1, part2, part3 = parts

    # Проверка первой части (сумма = 25)
    total = sum(int(c) if c.isdigit() else (ord(c) - ord('A') + 1) for c in part1)
    if total != 25:
        return False, 0

    # Проверка второй части (произведение кратно 10)
    product = 1
    has_two_or_five = False
    for c in part2:
        num = int(c) if c.isdigit() else (ord(c) - ord('A') + 1)
        product *= num
        if num in (2, 5):
            has_two_or_five = True
    if product % 10 != 0 or not has_two_or_five:
        return False, 0

    # Извлечение суммы из третьей части
    if len(part3) != 4:
        return False, 0

    y_char, z_char = part3[2], part3[3]
    tens = (ord(y_char) - ord('A') + 1) * 10  # A=10, B=20, ...
    units = (ord(z_char) - ord('A') + 1)      # A=1, B=2, ...
    coin_amount = tens + units

    return True, coin_amount

