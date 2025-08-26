import logging
import sys
import os
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """Форматтер для JSON-логов"""

    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


def get_logger(name: str = "app") -> logging.Logger:
    """Создание и настройка центрального логгера"""

    # Уровень логов задается через переменную окружения (по умолчанию INFO)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Формат для текстовых логов
    text_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Создается папка logs рядом с проектом
    LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / "app.log"

    # Центральный логгер
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Чтобы при повторных вызовах не дублировались хендлеры
    if logger.hasHandlers():
        logger.handlers.clear()

    # Консоль: человеко-читаемые логи (для разработки)
    console_handler = logging.StreamHandler(sys.stdout)

    if os.getenv("LOG_FORMAT", "TEXT").upper() == "JSON":
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(text_formatter)

    logger.addHandler(console_handler)

    # Файл: всегда текстовые логи с ротацией
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(text_formatter)
    logger.addHandler(file_handler)

    return logger


# === Центральный логгер для всего приложения ===
logger = get_logger()
