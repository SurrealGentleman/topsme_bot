import os
import json
from typing import Union, Dict, Any


_locales = {}
_locales_stage = {}

def get_message(lang: str, key: str, **kwargs) -> Union[str, Dict[str, Any]]:
    lang = lang.lower()
    if lang not in _locales:
        path = os.path.join(os.path.dirname(__file__), 'locales', f'{lang}.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                _locales[lang] = json.load(f)
        except FileNotFoundError:
            _locales[lang] = {}

    locale = _locales[lang]
    message = locale.get(key)

    if message is None:
        message = _locales.get("ru", {}).get(key, f"[{key}]")
        locale = _locales.get("ru", {})  # на случай если ключа нет в текущем языке

    # Получим карту меток VALUE_TYPE
    value_type_labels = locale.get("value_type_labels", {})

    # Обработка kwargs
    formatted_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, list) and all(isinstance(i, dict) for i in v):
            formatted_kwargs[k] = format_contact_field(v, value_type_labels)
        else:
            formatted_kwargs[k] = v

    if isinstance(message, dict):
        return message
    elif isinstance(message, str):
        try:
            return message.format(**formatted_kwargs)
        except (KeyError, ValueError):
            return message
    return message


def format_contact_field(items: list, labels_map: dict) -> str:
    """
    Преобразует список словарей в текст с использованием локализованных меток.
    """
    lines = []
    for item in items:
        value = item.get("VALUE")
        type_key = item.get("VALUE_TYPE", "OTHER").upper()
        label = labels_map.get(type_key, type_key.capitalize())
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)

def localize_stage_names(stages: list[dict], lang: str) -> list[dict]:
    lang = lang.lower()
    print(lang)
    print(_locales)
    if lang not in _locales:

        path = os.path.join(os.path.dirname(__file__), 'locales', f'{lang}.json')
        print(path)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                _locales[lang] = json.load(f)
        except FileNotFoundError:
            _locales[lang] = {}

    locale = _locales[lang]
    # message = locale.get(key)
    localized=[]
    for stage in stages:
        stage_id = stage["stage_id"]
        value_type_labels_stages = locale.get("value_type_labels_stages", {})
        name = value_type_labels_stages.get(stage_id, stage["name"])  # fallback: оригинальное имя
        localized.append({"stage_id": stage_id, "name": name})
    return localized

