# Кислощаев Дмитрий Михайлович
# Группа М26-555, вариант 14 (коллекции и экспонаты музея).
# Условия варианта: коллекция — название, описание, начало и конец показа.
# Экспонат — название, описание, страховая стоимость, век создания,
# принадлежность коллекции, выставочный зал, размеры (высота/ширина/длина),
# контроль температуры/влажности и защита от посетителей.
# В данной работе используются только две связанные таблицы:
# museum_collections и exhibits, без внешних связей с другими таблицами.
# Сессионный проект PostgreSQL на основе выданного эталона ProjectPostgreSQL.

"""Управление коллекциями и экспонатами через консольное меню."""

import sys

import psycopg2
import yaml

from dbconnection import DbConnection
from project_config import ProjectConfig
from tables.collections_table import CollectionsTable
from tables.exhibits_table import ExhibitsTable
from validation import century, date_range, decimal_amount, description, iso_date, required_text, yes_no

PAGE_SIZE = 8
NO_VALUE = object()


def display_value(value):
    if isinstance(value, bool):
        return "да" if value else "нет"
    if value is None or value == "":
        return "пусто"
    value = str(value)
    return value[:50] + "…" if len(value) > 51 else value


def prompt(label, validator, current=NO_VALUE, allow_clear=False):
    """Пока значение некорректное, повторяем ввод без запроса к PostgreSQL."""
    while True:
        default = "" if current is NO_VALUE else f" [{display_value(current)}]"
        try:
            value = input(f"{label}{default}: ")
        except (KeyboardInterrupt, EOFError):
            raise
        if current is not NO_VALUE and value == "":
            return current
        if allow_clear and value.strip() == "-":
            return ""
        try:
            return validator(value)
        except ValueError as exc:
            print("Некорректное значение:", exc)


def confirmation(question):
    while True:
        answer = input(question + " (да/нет) [нет]: ").strip()
        if not answer:
            return False
        try:
            return yes_no(answer)
        except ValueError as exc:
            print(exc)


def collection_data(existing=None):
    existing = existing or {}
    record = {
        "name": prompt("Название коллекции", lambda x: required_text(x, "Название коллекции"),
                       existing.get("name", NO_VALUE)),
        "short_description": prompt("Описание (для очистки введите -)", description,
                                    existing.get("short_description", ""), allow_clear=True),
    }
    while True:
        start = prompt("Начало показа (ГГГГ-ММ-ДД)", iso_date,
                       existing.get("display_start_date", NO_VALUE))
        finish = prompt("Окончание показа (ГГГГ-ММ-ДД)", iso_date,
                        existing.get("display_end_date", NO_VALUE))
        try:
            date_range(start, finish)
        except ValueError as exc:
            print(exc, "Введите даты повторно.")
            continue
        record["display_start_date"] = start
        record["display_end_date"] = finish
        return record


def exhibit_data(existing=None):
    existing = existing or {}
    record = {
        "name": prompt("Название экспоната", lambda x: required_text(x, "Название экспоната"),
                       existing.get("name", NO_VALUE)),
        "short_description": prompt("Описание (для очистки введите -)", description,
                                    existing.get("short_description", ""), allow_clear=True),
        "insurance_value_rub": prompt("Страховая стоимость (руб.)",
                                      lambda x: decimal_amount(x, "Стоимость", 12),
                                      existing.get("insurance_value_rub", NO_VALUE)),
        "creation_century": prompt("Век создания (-5 означает V век до н. э.)", century,
                                   existing.get("creation_century", NO_VALUE)),
        "hall_name": prompt("Выставочный зал", lambda x: required_text(x, "Зал"),
                            existing.get("hall_name", NO_VALUE)),
    }
    for key, label in (("height_cm", "Высота, см"),
                       ("width_cm", "Ширина, см"),
                       ("length_cm", "Длина, см")):
        record[key] = prompt(label,
                             lambda x, name=label: decimal_amount(x, name, 8, strictly_positive=True),
                             existing.get(key, NO_VALUE))
    for key, label in (("temperature_control_required", "Нужен контроль температуры?"),
                       ("humidity_control_required", "Нужен контроль влажности?"),
                       ("protected_from_visitors", "Защита от посетителей?")):
        record[key] = prompt(label + " (да/нет)", yes_no, existing.get(key, False))
    return record


def collection_summary(record):
    return (f"{record['name']} | период: "
            f"{record['display_start_date']} — {record['display_end_date']}")


def exhibit_summary(record):
    return (f"{record['name']} | {record['creation_century']} век | "
            f"{record['insurance_value_rub']} руб. | зал «{record['hall_name']}»")


def show_collection(record):
    print("\nКоллекция:", record["name"])
    print("Описание:", record["short_description"] or "—")
    print("Период показа:", record["display_start_date"], "—", record["display_end_date"])


def show_exhibit(record):
    print("\nЭкспонат:", record["name"])
    print("Описание:", record["short_description"] or "—")
    print("Страховая стоимость:", record["insurance_value_rub"], "руб.")
    print("Век создания:", record["creation_century"])
    print("Зал:", record["hall_name"])
    print("Размеры В × Ш × Д, см:", record["height_cm"], "×", record["width_cm"], "×", record["length_cm"])
    print("Контроль температуры:", display_value(record["temperature_control_required"]))
    print("Контроль влажности:", display_value(record["humidity_control_required"]))
    print("Защита от посетителей:", display_value(record["protected_from_visitors"]))


def browse(title, total_fn, page_fn, summary_fn):
    """Выбор по порядковому номеру НА ТЕКУЩЕЙ странице, не по id БД."""
    page = 0
    while True:
        total = total_fn()
        if not total:
            print("\nПока нет записей.")
            return None
        last_page = (total - 1) // PAGE_SIZE
        page = min(page, last_page)
        rows = page_fn(PAGE_SIZE, page * PAGE_SIZE)
        if not rows:  # возможна параллельная правка базы другим пользователем
            page = 0
            continue
        print(f"\n{title}: страница {page + 1} из {last_page + 1}, всего {total}")
        for position, record in enumerate(rows, 1):
            print(f"  {position}. {summary_fn(record)}")
        print("Введите номер строки; Д — дальше; Н — назад; 0 — отмена.")
        action = input("=> ").strip().lower()
        if action == "0":
            return None
        if action in ("д", "d", ">"):  # для латинской раскладки
            if page < last_page:
                page += 1
            else:
                print("Это последняя страница.")
        elif action in ("н", "n", "<"):
            if page > 0:
                page -= 1
            else:
                print("Это первая страница.")
        elif action.isascii() and action.isdecimal() and len(action) <= 4:
            number = int(action)
            if 1 <= number <= len(rows):
                return rows[number - 1]
            print("Такой строки на текущей странице нет.")
        else:
            print("Некорректная команда. Укажите номер строки из списка.")


def pg_message(exc):
    """Понятные ошибки вместо трассировки PostgreSQL и текста SQL-запроса."""
    pgcode = getattr(exc, "pgcode", None)
    name = getattr(getattr(exc, "diag", None), "constraint_name", None)
    if pgcode == "23503":
        return "Связанная запись уже отсутствует либо используется в другом месте."
    if pgcode == "23505":
        return "Такое уникальное значение уже существует."
    if pgcode == "23502":
        return "Не заполнено обязательное поле."
    if pgcode == "22001":
        return "Превышена максимальная длина текстового поля."
    if pgcode == "22003":
        return "Число выходит за допустимые границы."
    if pgcode in ("22007", "22008"):
        return "Неверно указана дата."
    if pgcode == "23514":
        notes = {
            "chk_collection_date_order": "Дата окончания должна быть не раньше начала.",
            "chk_collection_name_not_empty": "Название коллекции не может быть пустым.",
            "chk_exhibit_name_not_empty": "Название экспоната не может быть пустым.",
            "chk_exhibit_hall_not_empty": "Название зала не может быть пустым.",
            "chk_dimensions_positive": "Размеры экспоната должны быть положительными.",
            "chk_insurance_nonnegative": "Стоимость должна быть неотрицательной.",
            "chk_century_not_zero": "Век не может быть равен нулю.",
        }
        return notes.get(name, "Значение нарушает ограничения данных.")
    if pgcode in ("40001", "40P01", "55P03"):
        return "Другой процесс изменил данные. Повторите попытку."
    if pgcode in ("42P01", "42703", "42804", "42704", "42P07"):
        return "Структура таблиц отличается от ожидаемой. Проверьте схему БД."
    if pgcode == "42501":
        return "Недостаточно прав на таблицу или схему."
    return "Операция в PostgreSQL не выполнена. Проверьте данные и настройки сервера."


class Main:
    def __init__(self, connection):
        self.connection = connection
        self.collections = CollectionsTable(connection)
        self.exhibits = ExhibitsTable(connection)

    def db_init(self):
        # Обе таблицы создаются атомарно; при ошибке не останется половины схемы.
        with self.connection.conn:
            with self.connection.conn.cursor() as cursor:
                self.collections.create(cursor)
                self.exhibits.create(cursor)

    def select_collection(self):
        return browse("Коллекции", self.collections.count, self.collections.all, collection_summary)

    def select_exhibit(self, collection_id):
        return browse(
            "Экспонаты", lambda: self.exhibits.count_by_collection(collection_id),
            lambda limit, offset: self.exhibits.all_by_collection(collection_id, limit, offset),
            exhibit_summary,
        )

    def show_main_menu(self):
        print("""
МУЗЕЙ. Вариант 14 — коллекции и экспонаты
  1 — Просмотреть коллекции
  2 — Добавить коллекцию
  3 — Изменить коллекцию
  4 — Удалить коллекцию
  5 — Экспонаты выбранной коллекции
  9 — Выход""")

    def show_collections(self):
        selected = self.select_collection()
        if selected:
            show_collection(selected)

    def add_collection(self):
        record = collection_data()
        self.collections.insert_one(record)
        print("Коллекция добавлена.")

    def edit_collection(self):
        selected = self.select_collection()
        if selected:
            show_collection(selected)
            record = collection_data(selected)
            updated = self.collections.update_one(selected["collection_id"], record)
            print("Коллекция изменена." if updated else "Коллекция уже удалена другим пользователем.")

    def delete_collection(self):
        selected = self.select_collection()
        if selected:
            show_collection(selected)
            linked = self.exhibits.count_by_collection(selected["collection_id"])
            print("Вместе с коллекцией будут удалены её экспонаты:", linked)
            if confirmation("Удалить коллекцию и все связанные экспонаты?"):
                removed = self.collections.delete_with_exhibits(selected["collection_id"])
                print("Коллекция и её экспонаты удалены." if removed else "Коллекция уже удалена.")
            else:
                print("Удаление отменено.")

    def show_exhibits_by_collection(self):
        selected = self.select_collection()
        if not selected:
            return
        collection_id = selected["collection_id"]
        while True:
            print(f"\nЭкспонаты коллекции «{selected['name']}»")
            print("  1 — Просмотр\n  2 — Добавить\n  3 — Изменить (доп.)\n  4 — Удалить\n  0 — Назад")
            action = input("=> ").strip()
            if action == "0":
                return
            if action == "1":
                item = self.select_exhibit(collection_id)
                if item:
                    show_exhibit(item)
            elif action == "2":
                item = exhibit_data()
                item["collection_id"] = collection_id
                self.exhibits.insert_one(item)
                print("Экспонат добавлен.")
            elif action == "3":
                item = self.select_exhibit(collection_id)
                if item:
                    show_exhibit(item)
                    changed = self.exhibits.update_by_collection(
                        item["exhibit_id"], collection_id, exhibit_data(item)
                    )
                    print("Экспонат изменён." if changed else "Экспонат уже удалён.")
            elif action == "4":
                item = self.select_exhibit(collection_id)
                if item:
                    show_exhibit(item)
                    if confirmation("Удалить выбранный экспонат?"):
                        deleted = self.exhibits.delete_by_collection(item["exhibit_id"], collection_id)
                        print("Экспонат удалён." if deleted else "Экспонат уже удалён.")
                    else:
                        print("Удаление отменено.")
            else:
                print("Неизвестная команда.")

    def main_cycle(self):
        self.db_init()
        while True:
            self.show_main_menu()
            action = input("=> ").strip()
            if action == "9":
                print("До свидания!")
                return
            try:
                if action == "1":
                    self.show_collections()
                elif action == "2":
                    self.add_collection()
                elif action == "3":
                    self.edit_collection()
                elif action == "4":
                    self.delete_collection()
                elif action == "5":
                    self.show_exhibits_by_collection()
                else:
                    print("Неизвестная команда.")
            except (psycopg2.InterfaceError, psycopg2.OperationalError):
                print("Соединение с PostgreSQL потеряно. Проверьте сервер и перезапустите программу.")
                return
            except psycopg2.Error as exc:
                print("Ошибка:", pg_message(exc))
            except ValueError as exc:
                print("Ошибка ввода:", exc)


def main():
    try:
        config = ProjectConfig()
        connection = DbConnection(config)
    except (OSError, ValueError, KeyError, yaml.YAMLError, psycopg2.Error):
        print("Не удалось прочитать настройки или подключиться к PostgreSQL. Проверьте config.yaml и сервер.")
        return 1
    try:
        connection.ensure_schema()
        Main(connection).main_cycle()
    except (psycopg2.Error, ValueError) as exc:
        print("Ошибка подготовки проекта:", pg_message(exc) if isinstance(exc, psycopg2.Error) else str(exc))
        return 1
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nРабота завершена.")
        sys.exit(0)
