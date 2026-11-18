"""Запись новых PDF-файлов с классической таблицей перекрёстных ссылок."""

from dataclasses import dataclass

from core.pdf_engine.objects import Name, Reference, serialize_object


@dataclass(frozen=True)
class Stream:
    dictionary: dict
    data: bytes


def write_pdf(objects, root):
    """Записывает нумерованные объекты и ссылку на каталог в новый PDF.

    Создаёт только новые файлы: инкрементальные обновления, шифрование,
    подписи и сжатые потоки объектов существующего PDF не сохраняются.
    """
    if not isinstance(root, Reference) or root.generation != 0 or root.object_number not in objects:
        raise ValueError("Root must reference an object in the document")
    catalog = objects[root.object_number]
    if not isinstance(catalog, dict) or catalog.get(b"Type") != Name(b"Catalog"):
        raise ValueError("Root must reference a PDF catalog")
    if any(not isinstance(n, int) or isinstance(n, bool) or n <= 0 for n in objects):
        raise ValueError("Object numbers must be positive integers")
    if not objects or max(objects) > 1_000_000:
        raise ValueError("Invalid object number range")
    result = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for number, value in sorted(objects.items()):
        offsets[number] = len(result)
        result.extend(f"{number} 0 obj\n".encode("ascii"))
        if isinstance(value, Stream):
            if not isinstance(value.data, bytes):
                raise TypeError("PDF stream data must be bytes")
            dictionary = {**value.dictionary, b"Length": len(value.data)}
            result.extend(serialize_object(dictionary))
            result.extend(b"\nstream\n" + value.data + b"\nendstream")
        else:
            result.extend(serialize_object(value))
        result.extend(b"\nendobj\n")
    xref_offset = len(result)
    size = max(objects) + 1
    result.extend(f"xref\n0 {size}\n0000000000 65535 f \n".encode("ascii"))
    for number in range(1, size):
        if number in offsets:
            result.extend(f"{offsets[number]:010d} 00000 n \n".encode("ascii"))
        else:
            result.extend(b"0000000000 00000 f \n")
    result.extend(b"trailer\n")
    result.extend(serialize_object({b"Size": size, b"Root": root}))
    result.extend(f"\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(result)
