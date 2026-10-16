-- Домашнее задание ко второму модулю
-- ФИО: Кислощаев Дмитрий Михайлович
-- Группа: М26-555
-- Вариант: 14 (13 % 26 + 1 = 14)
-- СУБД: SQLite 3
--
-- Условия задания:
-- 1. Выбрать информацию о коллекциях (все поля таблицы), срок показа
--    которых от начала до конца не превышает 30 дней, отсортировав
--    результат по этому сроку в порядке возрастания.
-- 2. Выбрать номера или идентификаторы залов и число выставленных
--    в них коллекций.
--
-- Таблицы соответствуют домашнему заданию к первому модулю.
-- Скрипт рассчитан на запуск в отдельной базе: существующие таблицы
-- музея с теми же именами пересоздаются вместе с данными.
-- Даты хранятся в формате ГГГГ-ММ-ДД.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Удаляем дочерние таблицы раньше родительских, чтобы скрипт
-- можно было повторно выполнить с тем же результатом.
DROP TABLE IF EXISTS ticket_halls;
DROP TABLE IF EXISTS exhibits;
DROP TABLE IF EXISTS collection_halls;
DROP TABLE IF EXISTS ticket_prices;
DROP TABLE IF EXISTS museum_collections;
DROP TABLE IF EXISTS exhibition_halls;

-- 1. Выставочные залы
CREATE TABLE exhibition_halls (
    hall_id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    CONSTRAINT chk_hall_name_not_empty CHECK (LENGTH(TRIM(name)) > 0)
);

-- 2. Коллекции и периоды их показа
CREATE TABLE museum_collections (
    collection_id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    short_description TEXT NOT NULL DEFAULT '',
    display_start_date DATE NOT NULL,
    display_end_date DATE NOT NULL,
    CONSTRAINT chk_collection_name_not_empty CHECK (
        LENGTH(TRIM(name)) > 0
    ),
    CONSTRAINT chk_collection_date_order CHECK (
        display_end_date >= display_start_date
    ),
    -- Проверяем и формат, и действительность календарной даты.
    -- Модификатор '+0 days' нормализует невозможные даты вроде
    -- 2026-02-30; IS NOT NULL не даёт CHECK пропустить NULL.
    CONSTRAINT chk_collection_start_date CHECK (
        display_start_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND DATE(display_start_date, '+0 days') IS NOT NULL
        AND DATE(display_start_date, '+0 days') = display_start_date
    ),
    CONSTRAINT chk_collection_end_date CHECK (
        display_end_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND DATE(display_end_date, '+0 days') IS NOT NULL
        AND DATE(display_end_date, '+0 days') = display_end_date
    )
);

-- 3. Размещение коллекций в залах (связь многие ко многим)
CREATE TABLE collection_halls (
    collection_id INTEGER NOT NULL,
    hall_id INTEGER NOT NULL,
    PRIMARY KEY (collection_id, hall_id),
    FOREIGN KEY (collection_id) REFERENCES museum_collections (collection_id),
    FOREIGN KEY (hall_id) REFERENCES exhibition_halls (hall_id)
);

-- 4. Экспонаты
CREATE TABLE exhibits (
    exhibit_id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    short_description TEXT NOT NULL DEFAULT '',
    insurance_value_rub DECIMAL(14, 2) NOT NULL DEFAULT 0,
    creation_century SMALLINT NOT NULL,
    collection_id INTEGER NOT NULL,
    hall_id INTEGER NOT NULL,
    height_cm DECIMAL(10, 2) NOT NULL,
    width_cm DECIMAL(10, 2) NOT NULL,
    length_cm DECIMAL(10, 2) NOT NULL,
    temperature_control_required BOOLEAN NOT NULL DEFAULT 0,
    humidity_control_required BOOLEAN NOT NULL DEFAULT 0,
    protected_from_visitors BOOLEAN NOT NULL DEFAULT 0,
    CONSTRAINT chk_exhibit_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_insurance_nonnegative CHECK (insurance_value_rub >= 0),
    CONSTRAINT chk_century_not_zero CHECK (creation_century <> 0),
    CONSTRAINT chk_dimensions_positive CHECK (
        height_cm > 0 AND width_cm > 0 AND length_cm > 0
    ),
    CONSTRAINT chk_temperature_flag CHECK (temperature_control_required IN (0, 1)),
    CONSTRAINT chk_humidity_flag CHECK (humidity_control_required IN (0, 1)),
    CONSTRAINT chk_visitor_protection_flag CHECK (protected_from_visitors IN (0, 1)),
    FOREIGN KEY (collection_id, hall_id)
        REFERENCES collection_halls (collection_id, hall_id)
);

-- 5. Варианты билетов
CREATE TABLE ticket_prices (
    ticket_price_id INTEGER PRIMARY KEY,
    visitor_type VARCHAR(100) NOT NULL,
    price_rub DECIMAL(10, 2) NOT NULL,
    CONSTRAINT chk_visitor_type_not_empty CHECK (LENGTH(TRIM(visitor_type)) > 0),
    CONSTRAINT chk_ticket_price_nonnegative CHECK (price_rub >= 0)
);

-- 6. Залы, доступные по каждому билету
CREATE TABLE ticket_halls (
    ticket_price_id INTEGER NOT NULL,
    hall_id INTEGER NOT NULL,
    PRIMARY KEY (ticket_price_id, hall_id),
    FOREIGN KEY (ticket_price_id) REFERENCES ticket_prices (ticket_price_id),
    FOREIGN KEY (hall_id) REFERENCES exhibition_halls (hall_id)
);

-- Заполнение таблиц

INSERT INTO exhibition_halls (hall_id, name) VALUES
    (1, 'Зал древнего мира'),
    (2, 'Зал русского искусства'),
    (3, 'Зал графики'),
    (4, 'Зал естествознания'),
    (5, 'Зал истории техники'),
    (6, 'Зал временных выставок');

INSERT INTO museum_collections
    (collection_id, name, short_description, display_start_date, display_end_date)
VALUES
    (1, 'Античная керамика', 'Сосуды и бытовые предметы античных городов.', '2026-10-01', '2026-10-30'),
    (2, 'Русский портрет XIX века', 'Живописные портреты и их эскизы.', '2026-11-05', '2026-12-05'),
    (3, 'Городские зарисовки', 'Графика с видами городских улиц и площадей.', '2026-11-10', '2026-11-25'),
    (4, 'Минералы и горные породы', 'Образцы минералов из разных регионов.', '2026-10-01', '2027-01-15'),
    (5, 'История вычислительной техники', 'Приборы и устройства для вычислений.', '2026-12-01', '2027-01-01'),
    (6, 'Монеты древних государств', 'Монеты античного времени.', '2026-09-20', '2026-09-20'),
    (7, 'Современная скульптура', 'Работы российских скульпторов конца XX века.', '2026-11-01', '2026-12-01');

INSERT INTO collection_halls (collection_id, hall_id) VALUES
    (1, 1),
    (2, 2),
    (3, 2),
    (3, 3),
    (4, 4),
    (5, 5),
    (6, 1),
    (6, 3),
    (7, 2),
    (7, 5);

INSERT INTO exhibits
    (exhibit_id, name, short_description, insurance_value_rub,
     creation_century, collection_id, hall_id, height_cm, width_cm,
     length_cm, temperature_control_required, humidity_control_required,
     protected_from_visitors)
VALUES
    (1, 'Чернофигурная амфора', 'Керамический сосуд с росписью.', 520000, -6, 1, 1, 45, 27, 27, 0, 1, 1),
    (2, 'Глиняная масляная лампа', 'Небольшой светильник античного периода.', 85000, -2, 1, 1, 8, 10, 15, 0, 0, 1),
    (3, 'Портрет купца', 'Холст, масло.', 1100000, 19, 2, 2, 92, 71, 4, 1, 1, 1),
    (4, 'Карандашный этюд', 'Подготовительный портретный рисунок.', 160000, 19, 2, 2, 30, 21, 1, 1, 1, 1),
    (5, 'Вид на городскую площадь', 'Графический лист с городским пейзажем.', 120000, 20, 3, 3, 40, 50, 1, 1, 1, 1),
    (6, 'Уличный набросок', 'Бумага, тушь.', 70000, 20, 3, 2, 25, 18, 1, 1, 1, 1),
    (7, 'Кристалл кварца', 'Природный образец прозрачного кварца.', 35000, 20, 4, 4, 16, 11, 10, 0, 0, 1),
    (8, 'Механический арифмометр', 'Настольное счетное устройство.', 240000, 20, 5, 5, 18, 32, 36, 0, 0, 1),
    (9, 'Серебряная драхма', 'Античная серебряная монета.', 210000, -4, 6, 1, 1, 2, 2, 0, 1, 1),
    (10, 'Композиция из бронзы', 'Малая скульптурная форма.', 430000, 20, 7, 2, 54, 25, 30, 0, 0, 1);

INSERT INTO ticket_prices (ticket_price_id, visitor_type, price_rub) VALUES
    (1, 'Взрослый', 600),
    (2, 'Студент', 300),
    (3, 'Школьник', 200),
    (4, 'Пенсионер', 250),
    (5, 'Ребенок до 7 лет', 0),
    (6, 'Взрослый с экскурсией', 900);

INSERT INTO ticket_halls (ticket_price_id, hall_id) VALUES
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6),
    (2, 1), (2, 2), (2, 3), (2, 5),
    (3, 1), (3, 4),
    (4, 1), (4, 2), (4, 3),
    (5, 1), (5, 2),
    (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6);

COMMIT;

-- Задание 1. Коллекции с периодом показа не более 30 дней.
-- Продолжительность определяется разностью дат окончания и начала.
-- При одинаковой продолжительности используется сортировка по ID.
SELECT c.*
FROM museum_collections AS c
WHERE JULIANDAY(c.display_end_date) - JULIANDAY(c.display_start_date) <= 30
ORDER BY
    JULIANDAY(c.display_end_date) - JULIANDAY(c.display_start_date) ASC,
    c.collection_id ASC;

-- Задание 2. Количество коллекций в каждом зале.
-- LEFT JOIN позволяет показать и залы без коллекций (число 0).
SELECT
    h.hall_id,
    COUNT(ch.collection_id) AS collection_count
FROM exhibition_halls AS h
LEFT JOIN collection_halls AS ch ON ch.hall_id = h.hall_id
GROUP BY h.hall_id
ORDER BY h.hall_id ASC;
