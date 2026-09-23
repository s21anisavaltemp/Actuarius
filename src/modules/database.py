"""
Модуль для работы с JSON-базой обработанных файлов.

Хранит два раздельных JSON-файла: для txt и для wav.
В каждом — словарь вида {имя_файла: bool}, где True означает "обработан".

Пример использования:
    import file_db

    file_db.init_db("db")               # создаст db_txt.json и db_wav.json при необходимости
    file_db.mark_processed("db", "a.txt", "txt")
    file_db.is_processed("db", "a.txt", "txt")   # True
    file_db.list_unprocessed("db", ["a.txt", "b.txt"], "txt")  # ["b.txt"]
"""

import json
import os
from typing import Iterable

# Допустимые типы файлов (важно только чтобы определить в какой json складывать имя файла)
_VALID_TYPES = ("txt", "wav")


def _db_path(database_path: str, file_type: str) -> str:
    """Возвращает путь к JSON-файлу базы для указанного типа."""
    if file_type not in _VALID_TYPES:
        raise ValueError(f"Неизвестный тип файла: {file_type!r}. Допустимо: {_VALID_TYPES}")
    return f"{database_path}/processed_{file_type}.json"


def _load(database_path: str, file_type: str) -> dict:
    """Загружает базу. Если файла нет — создаёт пустой и предупреждает. Возвращает объект из json соответствующего файла."""
    path = _db_path(database_path, file_type)
    if not os.path.exists(path):
        print(f"[file_db] Файл базы {path!r} не найден, будет создан новый!.")
        _save(database_path, file_type, {})
        return {}

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Файл базы {path!r} повреждён: {e}") from e

    if not isinstance(data, dict):
        raise RuntimeError(f"Файл базы {path!r} имеет неверный формат (ожидался объект json).")
    return data


def _save(database_path: str, file_type: str, data: dict) -> None:
    """Атомарно сохраняет базу."""
    path = _db_path(database_path, file_type)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def init_db(database_path: str) -> None:
    """Инициализирует обе базы (создаёт файлы, если их нет)."""
    for file_type in _VALID_TYPES:
        _load(database_path, file_type)


def is_processed(database_path: str, filename: str, file_type: str) -> bool:
    """Проверяет, помечен ли файл как обработанный."""
    data = _load(database_path, file_type)
    return data.get(filename, False) is True


def mark_processed(database_path: str, filename: str, file_type: str) -> None:
    """Помечает файл как обработанный и сохраняет базу."""
    data = _load(database_path, file_type)
    data[filename] = True
    _save(database_path, file_type, data)


def mark_unprocessed(database_path: str, filename: str, file_type: str) -> None:
    """Помечает файл как необработанный и сохраняет базу."""
    data = _load(database_path, file_type)
    data[filename] = False
    _save(database_path, file_type, data)


def list_processed(database_path: str, file_type: str) -> list[str]:
    """Возвращает список имён обработанных файлов."""
    data = _load(database_path, file_type)
    return [name for name, flag in data.items() if flag]


def list_unprocessed(database_path: str, file_type: str) -> list[str]:
    """Возвращает список имён необработанных файлов."""
    data = _load(database_path, file_type)
    return [name for name, flag in data.items() if flag == False]


def sync_with_folder(database_path: str, folder: str, file_type: str) -> list[str]:
    """
    Синхронизирует базу с содержимым папки.

    Читает все имена файлов в folder и добавляет в базу те, которых там ещё нет,
    помечая их как обработанные (mark_processed).

    Возвращает список имён файлов, которые были добавлены.
    """
    if file_type not in _VALID_TYPES:
        raise ValueError(f"Неизвестный тип файла: {file_type!r}. Допустимо: {_VALID_TYPES}")

    if not os.path.isdir(folder):
        raise NotADirectoryError(f"Папка не найдена: {folder!r}")

    data = _load(database_path, file_type)

    added: list[str] = []
    for entry in os.listdir(folder):
        full_path = os.path.join(folder, entry)
        if not os.path.isfile(full_path):
            continue
        if entry not in data:
            data[entry] = False
            added.append(entry)

    if added:
        _save(database_path, file_type, data)

    return added
