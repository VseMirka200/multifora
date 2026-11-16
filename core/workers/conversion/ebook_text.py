"""Чтение текста электронных книг без PDF-библиотек."""

import posixpath
import struct
from xml.etree import ElementTree as ET
from zipfile import ZipFile


def _read_mobi(data: bytes, html_to_text) -> str:
    if len(data) < 78:
        raise ValueError("Повреждён заголовок MOBI")
    count = struct.unpack_from(">H", data, 76)[0]
    if count < 2 or len(data) < 78 + count * 8:
        raise ValueError("Повреждена таблица записей MOBI")
    offsets = [struct.unpack_from(">I", data, 78 + index * 8)[0] for index in range(count)] + [len(data)]
    if offsets != sorted(offsets) or offsets[-1] > len(data):
        raise ValueError("Некорректные записи MOBI")
    header = data[offsets[0] : offsets[1]]
    if len(header) < 16:
        raise ValueError("Повреждён заголовок текста MOBI")
    compression, _, text_length, text_records, _, encryption = struct.unpack_from(">HHIHHH", header)
    if encryption:
        raise ValueError("Защищённые книги MOBI не поддерживаются")
    if compression not in {1, 2}:
        raise ValueError("Сжатие этой книги MOBI не поддерживается")
    if text_records > count - 1:
        raise ValueError("Повреждены текстовые записи MOBI")
    output = bytearray()
    for index in range(1, text_records + 1):
        data_record = data[offsets[index] : offsets[index + 1]]
        if compression == 1:
            output.extend(data_record)
            continue
        position = 0
        while position < len(data_record):
            value = data_record[position]
            position += 1
            if 1 <= value <= 8:
                if position + value > len(data_record):
                    raise ValueError("Повреждена сжатая запись MOBI")
                output.extend(data_record[position : position + value])
                position += value
            elif value <= 0x7F:
                output.append(value)
            elif value >= 0xC0:
                output.extend((32, value ^ 0x80))
            else:
                if position >= len(data_record):
                    raise ValueError("Повреждена сжатая запись MOBI")
                pair = value * 256 + data_record[position]
                position += 1
                distance, length = (pair >> 3) & 0x7FF, (pair & 7) + 3
                if not distance or distance > len(output):
                    raise ValueError("Повреждена ссылка в записи MOBI")
                for _ in range(length):
                    output.append(output[-distance])
    encoding = struct.unpack_from(">I", header, 28)[0] if len(header) >= 32 and header[16:20] == b"MOBI" else 1252
    return html_to_text(
        bytes(output[:text_length]).decode("utf-8" if encoding == 65001 else "cp1252", errors="replace")
    )


def read_ebook_text(path: str, source_format: str, html_to_text) -> str:
    if source_format == "MOBI":
        with open(path, "rb") as stream:
            return _read_mobi(stream.read(), html_to_text)
    if source_format == "FB2":
        root = ET.parse(path).getroot()
        return "\n".join(
            "".join(node.itertext()).strip() for node in root.iter() if node.tag.rsplit("}", 1)[-1] in {"p", "subtitle"}
        )
    if source_format == "EPUB":
        with ZipFile(path) as archive:
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            rootfile = next(
                node.get("full-path") for node in container.iter() if node.tag.rsplit("}", 1)[-1] == "rootfile"
            )
            package = ET.fromstring(archive.read(rootfile))
            manifest = {
                node.get("id"): node.get("href") for node in package.iter() if node.tag.rsplit("}", 1)[-1] == "item"
            }
            spine = [node.get("idref") for node in package.iter() if node.tag.rsplit("}", 1)[-1] == "itemref"]
            chapters = []
            for item in spine:
                href = manifest.get(item)
                if href:
                    name = posixpath.normpath(posixpath.join(posixpath.dirname(rootfile), href.split("#", 1)[0]))
                    chapters.append(html_to_text(archive.read(name).decode("utf-8", errors="replace")))
            return "\n\n".join(chapters)
    if source_format == "XPS":
        with ZipFile(path) as archive:
            pages = sorted(name for name in archive.namelist() if name.lower().endswith(".fpage"))
            texts = []
            for page in pages:
                root = ET.fromstring(archive.read(page))
                texts.append(
                    " ".join(
                        node.get("UnicodeString", "") for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "Glyphs"
                    )
                )
            return "\n\n".join(texts)
    raise ValueError(f"Не найден движок для чтения формата {source_format}")
