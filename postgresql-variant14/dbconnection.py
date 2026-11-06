"""Соединение с PostgreSQL (переработанный модуль эталонного проекта)."""

import psycopg2
from psycopg2 import sql


class DbConnection:
    def __init__(self, config):
        self.schema = config.dbtableprefix.rstrip(".")
        self.conn = psycopg2.connect(
            dbname=config.dbname,
            user=config.user,
            password=config.password,
            host=config.host,
            port=config.port,
            connect_timeout=5,
        )

    def close(self):
        if not self.conn.closed:
            self.conn.close()

    def test(self):
        """Проверка соединения без создания/удаления посторонних таблиц."""
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                return cur.fetchone()[0] == 1

    def ensure_schema(self):
        """В рабочей базе схема должна существовать и быть доступна пользователю."""
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute("SELECT to_regnamespace(%s)", (self.schema,))
                if cur.fetchone()[0] is None:
                    raise ValueError(
                        f"Схемы «{self.schema}» нет в базе. Измените dbtableprefix в config.yaml."
                    )

    def identifier(self, table_name):
        return sql.Identifier(self.schema, table_name)
