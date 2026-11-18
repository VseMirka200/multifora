"""Правила имён и папок результата, общие для предпросмотра и записи."""

import os

CONVERTED_FOLDER_NAME = "Конвертированные"


def conversion_directory(source_folder: str, mode: str, custom_dir: str) -> str:
    if mode == "custom" and custom_dir:
        return custom_dir
    if mode == "alongside":
        return source_folder
    return os.path.join(source_folder, CONVERTED_FOLDER_NAME)


def converted_name(name: str, extension: str) -> str:
    if not extension:
        return name
    return os.path.splitext(name)[0] + extension


def compressed_name(name: str, extension: str) -> str:
    if extension and not extension.startswith("."):
        extension = "." + extension
    return os.path.splitext(name)[0] + "_compressed" + extension
