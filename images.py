from typing import Tuple, Optional, Union, List
from PIL import Image, ImageDraw, ImageFont
import logging

import configs

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_coupon(rarity: str, title: str, description: str, effect: str, coupon_number: str,
                  coupon_code: str,
                  output_path: str = "coupon.png", template_paths: Optional[dict] = None,
                  main_font_path: str = r"font\HUMakingfilm Bold.otf",
                  stub_font_path: str = "arial.ttf",
                  description_font_path: str = r"font\Stonehenge.ttf",
                  main_path: str = "arial.ttf",
                  title_position: Tuple[int, int] = (350, 50), title_font_size: int = 60,
                  effect_position: Tuple[int, int] = (350, 150), effect_font_size: int = 30,
                  description_position: Tuple[int, int] = (350, 250),
                  description_font_size: int = 25,
                  description_max_width: int = 1200, number_position: Tuple[int, int] = (100, 50),
                  code_position: Tuple[int, int] = (100, 150), stub_font_size: int = 30,
                  stub_text_angle: int = 90, title_color: str = "black",
                  effect_color: str = "black",
                  description_color: str = "black", stub_text_color: str = "black",
                  collection_type: str = None) -> None:
    """
    Создает изображение купона с указанными параметрами.
    """
    try:
        # Преобразуем все текстовые параметры в строки
        def ensure_str(value: Union[str, int]) -> str:
            return str(value) if value is not None else ""

        title = ensure_str(title)
        description = ensure_str(description)
        effect = ensure_str(effect)
        coupon_number = ensure_str(coupon_number)
        coupon_code = ensure_str(coupon_code)
        collection_type = ensure_str(collection_type)

        logger.info(f"Начало создания купона: {title}")

        template_path = configs.template_paths.get(rarity.lower())
        if not template_path:
            raise ValueError(
                f"Неизвестная редкость: {rarity}. Допустимые значения: {list(template_paths.keys())}")

        logger.info(f"Создание купона редкости '{rarity}' с названием '{title}'")

        # Загрузка шаблона
        try:
            with Image.open(template_path) as img:
                coupon_img = img.copy()
                draw = ImageDraw.Draw(coupon_img)

                # Загрузка шрифтов
                def load_font(font_path: str, size: int,
                              italic: bool = False) -> ImageFont.FreeTypeFont:
                    try:
                        if italic:
                            italic_path = font_path.replace('.ttf', 'i.ttf')
                            try:
                                return ImageFont.truetype(italic_path, size)
                            except IOError:
                                font = ImageFont.truetype(font_path, size)
                                return font
                        return ImageFont.truetype(font_path, size)
                    except IOError:
                        logger.warning(f"Шрифт {font_path} не найден, используется стандартный")
                        return ImageFont.load_default(size)

                title_font = load_font(main_font_path, title_font_size)
                effect_font = load_font(main_path, effect_font_size)
                description_font = load_font(main_path, description_font_size, italic=True)
                stub_font = load_font(stub_font_path, stub_font_size)

                # Добавление основного текста
                draw.text(title_position, title, fill=title_color, font=title_font)

                # Функция для переноса текста
                def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
                    lines = []
                    if not text:
                        return lines

                    words = text.split()
                    current_line = []

                    for word in words:
                        test_line = ' '.join(current_line + [word])
                        width = draw.textlength(test_line, font=font)
                        if width <= max_width:
                            current_line.append(word)
                        else:
                            lines.append(' '.join(current_line))
                            current_line = [word]

                    if current_line:
                        lines.append(' '.join(current_line))

                    return lines

                # Добавление эффекта с переносом
                wrapped_effect = wrap_text(effect, effect_font, description_max_width)
                y_effect_offset = effect_position[1]
                for line in wrapped_effect:
                    draw.text((effect_position[0], y_effect_offset), line, fill=effect_color,
                              font=effect_font)
                    y_effect_offset += effect_font_size + 5

                # Добавление описания
                wrapped_description = wrap_text(description, description_font,
                                                description_max_width)
                y_desc_offset = max(description_position[1], y_effect_offset + 20)
                for line in wrapped_description:
                    draw.text((description_position[0], y_desc_offset), line,
                              fill=description_color,
                              font=description_font)
                    y_desc_offset += description_font_size + 5

                # Функция для добавления вертикального текста на корешок
                def add_stub_text(text: str, x: int, y: int) -> int:
                    if not text:
                        return 0

                    # Создаем временное изображение с текстом
                    temp_img = Image.new('RGBA', (500, 500), (0, 0, 0, 0))
                    temp_draw = ImageDraw.Draw(temp_img)
                    temp_draw.text((10, 10), text, fill=stub_text_color, font=stub_font)

                    # Обрезаем по границам текста
                    bbox = temp_img.getbbox()
                    if not bbox:
                        return 0

                    cropped_img = temp_img.crop(bbox)

                    # Поворачиваем текст
                    rotated_img = cropped_img.rotate(stub_text_angle, expand=True,
                                                     resample=Image.BICUBIC)

                    # Вставляем на основное изображение
                    coupon_img.paste(rotated_img, (x, y), rotated_img)

                    # Возвращаем высоту добавленного текста
                    return rotated_img.height

                # Размещаем текст на корешке
                current_y = number_position[1]
                vertical_spacing = 30

                # Коллекция
                if collection_type:
                    text_height = add_stub_text(f"Коллекция: {collection_type}", number_position[0],
                                                current_y)
                    current_y += text_height + vertical_spacing

                # Номер купона
                # if coupon_number:
                #     text_height = add_stub_text(f"Номер: {coupon_number}", number_position[0],
                #                                 current_y)
                #     current_y += text_height + vertical_spacing

                # Код купона
                if coupon_code:
                    add_stub_text(f"Код: {coupon_code}", code_position[0], current_y)

                # Сохранение результата
                coupon_img.save(output_path)
                logger.info(f"Купон успешно сохранен: {output_path}")

        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {str(e)}", exc_info=True)
            raise

    except Exception as e:
        logger.error(f"Критическая ошибка при создании купона: {str(e)}", exc_info=True)
        raise