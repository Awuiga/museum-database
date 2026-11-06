"""Проверки пользовательского ввода для музейного справочника."""

from datetime import date
from decimal import Decimal, InvalidOperation
import re


def check_text_characters(value: str) -> None:
    """Проверка символов, которые PostgreSQL не принимает в текстовых полях."""
    if "\x00" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("Текст содержит недопустимый управляющий символ.")


def required_text(value: str, label: str, limit: int = 200) -> str:
    check_text_characters(value)
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"Поле «{label}» не может быть пустым.")
    if len(cleaned) > limit:
        raise ValueError(f"Поле «{label}»: максимум {limit} символов.")
    return cleaned


def description(value: str) -> str:
    check_text_characters(value)
    return value.strip()


def iso_date(value: str) -> date:
    value = value.strip()
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Дата должна быть в формате ГГГГ-ММ-ДД.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Такой календарной даты не существует.") from exc


def date_range(start: date, end: date) -> None:
    if end < start:
        raise ValueError("Дата окончания показа не может быть раньше начала.")


def decimal_amount(
    value: str,
    label: str,
    integer_places: int,
    *,
    strictly_positive: bool = False,
) -> Decimal:
    """Без округления: формат соответствует NUMERIC(n, 2) в PostgreSQL."""
    value = value.strip().replace(",", ".")
    # Ограничение длины защищает от чрезмерно длинного пользовательского ввода.
    # Проверяем разрядность по строке, не преобразуя число в огромный int.
    if len(value) > 1000:
        raise ValueError(f"«{label}»: слишком длинное числовое значение.")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value):
        raise ValueError(f"«{label}»: нужно неотрицательное число (до 2 знаков после точки).")
    integral = value.split(".", 1)[0].lstrip("0") or "0"
    if len(integral) > integer_places:
        raise ValueError(f"«{label}»: слишком большое число.")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"«{label}»: неверное число.") from exc
    if strictly_positive and number <= 0:
        raise ValueError(f"«{label}» должно быть больше нуля.")
    return number


def century(value: str) -> int:
    value = value.strip()
    if not re.fullmatch(r"-?[0-9]{1,5}", value):
        raise ValueError("Век укажите целым числом: например, 18 или -5.")
    number = int(value)
    if number == 0 or not (-32768 <= number <= 32767):
        raise ValueError("Век не может быть нулевым и должен помещаться в SMALLINT.")
    return number


def yes_no(value: str) -> bool:
    yes = {"да", "д", "1", "yes", "y"}
    no = {"нет", "н", "0", "no", "n"}
    normalized = value.strip().casefold()
    if normalized in yes:
        return True
    if normalized in no:
        return False
    raise ValueError("Ответьте «да» или «нет» (можно 1/0).")
