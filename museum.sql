-- Домашнее задание к первому модулю: проектирование базы данных
-- ФИО: Кислощаев Дмитрий Михайлович
-- Группа: М26-555
-- Вариант: 14 (день рождения 13; 13 % 26 + 1 = 14)
-- СУБД: SQLite 3
--
-- Условия варианта 14.
-- Предметная область: коллекции и экспонаты музея.
-- 1. Выставочный зал имеет название.
-- 2. Коллекция имеет название, краткое описание, период показа
--    (даты начала и окончания) и может размещаться в нескольких залах.
-- 3. Экспонат имеет название, краткое описание, страховую стоимость,
--    век создания, принадлежность к коллекции и выставочному залу,
--    размеры (высота, ширина, длина), признаки необходимости контроля
--    температуры и влажности, признак защищенности от посетителей.
-- 4. Стоимость билета определяется типом посетителя, набором
--    доступных по этому билету ЗАЛОВ и ценой в рублях.
--    Вариант 14 отличается от варианта 13 тем, что доступ дается
--    к залам, а не непосредственно к коллекциям.
--
-- Таблицы:
--   exhibition_halls   - выставочные залы;
--   museum_collections - коллекции;
--   collection_halls   - размещение коллекций в залах (многие ко многим);
--   exhibits           - экспонаты;
--   ticket_prices      - варианты билетов и их цены;
--   ticket_halls       - доступные по билету залы (многие ко многим).
--
-- Формат дат: ГГГГ-ММ-ДД (ISO 8601).
-- Размеры указаны в сантиметрах, денежные суммы - в рублях.
-- Логические признаки представлены числами 0 (нет) и 1 (да).
-- Флаг внешних ключей включается отдельно, как требуется в SQLite.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- 1. Выставочные залы
CREATE TABLE exhibition_halls (
    hall_id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    CONSTRAINT chk_hall_name_not_empty CHECK (LENGTH(TRIM(name)) > 0)
);

-- 2. Музейные коллекции с периодами показа
CREATE TABLE museum_collections (
    collection_id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    short_description TEXT NOT NULL DEFAULT '',
    display_start_date DATE NOT NULL,
    display_end_date DATE NOT NULL,
    CONSTRAINT chk_collection_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_collection_date_order CHECK (
        display_end_date >= display_start_date
    ),
    CONSTRAINT chk_collection_start_date CHECK (
        DATE(display_start_date, '+0 days') IS NOT NULL
        AND display_start_date = DATE(display_start_date, '+0 days')
    ),
    CONSTRAINT chk_collection_end_date CHECK (
        DATE(display_end_date, '+0 days') IS NOT NULL
        AND display_end_date = DATE(display_end_date, '+0 days')
    )
);

-- 3. В каких залах размещается каждая коллекция
CREATE TABLE collection_halls (
    collection_id INTEGER NOT NULL,
    hall_id INTEGER NOT NULL,
    PRIMARY KEY (collection_id, hall_id),
    FOREIGN KEY (collection_id)
        REFERENCES museum_collections (collection_id),
    FOREIGN KEY (hall_id)
        REFERENCES exhibition_halls (hall_id)
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
    CONSTRAINT chk_temperature_flag CHECK (
        temperature_control_required IN (0, 1)
    ),
    CONSTRAINT chk_humidity_flag CHECK (
        humidity_control_required IN (0, 1)
    ),
    CONSTRAINT chk_visitor_protection_flag CHECK (
        protected_from_visitors IN (0, 1)
    ),
    -- Экспонат может находиться только в зале, в котором
    -- представлена его коллекция.
    FOREIGN KEY (collection_id, hall_id)
        REFERENCES collection_halls (collection_id, hall_id)
);

-- 5. Варианты стоимости билетов
-- Одинаковый тип посетителя может иметь билеты с разным набором залов.
CREATE TABLE ticket_prices (
    ticket_price_id INTEGER PRIMARY KEY,
    visitor_type VARCHAR(100) NOT NULL,
    price_rub DECIMAL(10, 2) NOT NULL,
    CONSTRAINT chk_visitor_type_not_empty CHECK (
        LENGTH(TRIM(visitor_type)) > 0
    ),
    CONSTRAINT chk_ticket_price_nonnegative CHECK (price_rub >= 0)
);

-- 6. Набор залов, доступных по каждому варианту билета
CREATE TABLE ticket_halls (
    ticket_price_id INTEGER NOT NULL,
    hall_id INTEGER NOT NULL,
    PRIMARY KEY (ticket_price_id, hall_id),
    FOREIGN KEY (ticket_price_id)
        REFERENCES ticket_prices (ticket_price_id),
    FOREIGN KEY (hall_id)
        REFERENCES exhibition_halls (hall_id)
);

COMMIT;
