"""Загрузка параметров подключения из config.yaml эталонного проекта."""

import os
from pathlib import Path
import re

import yaml


class ProjectConfig:
    def __init__(self):
        config_path = Path(__file__).with_name("config.yaml")
        with config_path.open(encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        if not isinstance(config, dict):
            raise ValueError("Файл config.yaml должен содержать параметры подключения.")

        self.dbname = os.getenv("PGDATABASE", str(config.get("dbname", "postgres")))
        self.user = os.getenv("PGUSER", str(config.get("user", "postgres")))
        self.password = os.getenv("PGPASSWORD", str(config.get("password", "")))
        self.host = os.getenv("PGHOST", str(config.get("host", "localhost")))
        port = os.getenv("PGPORT", str(config.get("port", "5432")))
        if not port.isdecimal() or not 1 <= int(port) <= 65535:
            raise ValueError("Порт PostgreSQL должен быть числом от 1 до 65535.")
        self.port = int(port)

        schema_name = str(config.get("dbtableprefix", "public.")).rstrip(".")
        if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", schema_name) is None:
            raise ValueError("dbtableprefix должен содержать одно имя схемы, например public.")
        self.dbtableprefix = schema_name + "."


if __name__ == "__main__":
    cfg = ProjectConfig()
    print("База:", cfg.dbname, "Пользователь:", cfg.user, "Схема:", cfg.dbtableprefix)
