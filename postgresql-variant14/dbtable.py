"""Базовые операции с таблицами на основе DbTable из эталонного проекта.

Имена таблиц/полей задаются только в коде; значения всегда идут отдельными
параметрами (%s) — пользовательский ввод не попадает в текст SQL-запроса.
"""

from psycopg2 import sql
from psycopg2.extras import RealDictCursor


class DbTable:
    def __init__(self, dbconn):
        self.dbconn = dbconn

    @property
    def name(self):
        raise NotImplementedError

    def table_name(self):
        return self.dbconn.schema + "." + self.name

    @property
    def table_sql(self):
        return self.dbconn.identifier(self.name)

    def columns(self):
        raise NotImplementedError

    def column_names_without_id(self):
        # Только поля, явно разрешённые разработчиком; ключи не запрашиваются.
        return list(self.columns())

    def primary_key(self):
        raise NotImplementedError

    def create(self, cursor):
        raise NotImplementedError

    def insert_one(self, record):
        """Добавление. id генерирует PostgreSQL, пользователь не вводит его."""
        cols = self.column_names_without_id()
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}").format(
            self.table_sql,
            sql.SQL(", ").join(map(sql.Identifier, cols)),
            sql.SQL(", ").join([sql.Placeholder()] * len(cols)),
            sql.Identifier(self.primary_key()),
        )
        params = tuple(record[column] for column in cols)
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()[0]

    def update_one(self, record_id, record):
        cols = self.column_names_without_id()
        assignments = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            for col in cols
        )
        query = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
            self.table_sql, assignments, sql.Identifier(self.primary_key())
        )
        params = tuple(record[col] for col in cols) + (record_id,)
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.rowcount

    def delete_one(self, record_id):
        query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
            self.table_sql, sql.Identifier(self.primary_key())
        )
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cursor:
                cursor.execute(query, (record_id,))
                return cursor.rowcount

    def count(self):
        with self.dbconn.conn:
            with self.dbconn.conn.cursor() as cursor:
                cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(self.table_sql))
                return cursor.fetchone()[0]

    def all(self, limit=8, offset=0):
        """Вывод страницы без суррогатных ключей в меню."""
        if not (1 <= limit <= 100) or offset < 0:
            raise ValueError("Некорректные параметры страницы.")
        query = sql.SQL("SELECT * FROM {} ORDER BY lower(name), {} LIMIT %s OFFSET %s").format(
            self.table_sql, sql.Identifier(self.primary_key())
        )
        with self.dbconn.conn:
            with self.dbconn.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (limit, offset))
                return list(cursor.fetchall())

    def find_by_position(self, position, limit=8, offset=0):
        """Номер в списке преобразуется во внутренний ключ, а не вводится пользователем."""
        if not 1 <= position <= limit:
            return None
        rows = self.all(limit=limit, offset=offset)
        return rows[position - 1] if position <= len(rows) else None
