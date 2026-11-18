"""Разбор синтаксиса PDF на токены; содержимое потоков обрабатывается отдельно."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str
    value: bytes
    offset: int


_SPACE = b"\x00\x09\x0a\x0c\x0d\x20"
_DELIMITERS = b"()<>[]{}/%"


def tokenize(data: bytes):
    """Выдаёт токены синтаксиса объектов PDF, сохраняя значения байтов."""
    i = 0
    while i < len(data):
        c = data[i]
        if c in _SPACE:
            i += 1
            continue
        if c == ord("%"):
            while i < len(data) and data[i] not in b"\r\n":
                i += 1
            continue
        start = i
        if c == ord("("):
            i += 1
            depth = 1
            value = bytearray()
            while i < len(data) and depth:
                c = data[i]
                i += 1
                if c == ord("\\"):
                    if i == len(data):
                        raise ValueError("Unterminated PDF string escape")
                    c = data[i]
                    i += 1
                    escapes = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
                    if c in b"\r\n":
                        if c == 13 and i < len(data) and data[i] == 10:
                            i += 1
                    elif 48 <= c <= 55:
                        digits = bytes([c])
                        while len(digits) < 3 and i < len(data) and 48 <= data[i] <= 55:
                            digits += bytes([data[i]])
                            i += 1
                        value.append(int(digits, 8) & 255)
                    else:
                        value.append(escapes.get(c, c))
                elif c == ord("("):
                    depth += 1
                    value.append(c)
                elif c == ord(")"):
                    depth -= 1
                    if depth:
                        value.append(c)
                else:
                    value.append(c)
            if depth:
                raise ValueError("Unterminated PDF string")
            yield Token("string", bytes(value), start)
            continue
        if data[i:i + 2] in (b"<<", b">>"):
            yield Token("delimiter", data[i:i + 2], start)
            i += 2
            continue
        if c == ord("<"):
            end = data.find(b">", i + 1)
            if end < 0:
                raise ValueError("Unterminated PDF hex string")
            digits = bytes(x for x in data[i + 1:end] if x not in _SPACE)
            if len(digits) % 2:
                digits += b"0"
            try:
                value = bytes.fromhex(digits.decode("ascii"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("Invalid PDF hex string") from exc
            yield Token("string", value, start)
            i = end + 1
            continue
        if c == ord("/"):
            i += 1
            value = bytearray()
            while i < len(data) and data[i] not in _SPACE + _DELIMITERS:
                if data[i] == ord("#") and i + 2 < len(data):
                    try:
                        value.append(int(data[i + 1:i + 3], 16))
                    except ValueError:
                        raise ValueError("Invalid PDF name escape") from None
                    i += 3
                elif data[i] == ord("#"):
                    raise ValueError("Invalid PDF name escape")
                else:
                    value.append(data[i])
                    i += 1
            yield Token("name", bytes(value), start)
            continue
        if c in _DELIMITERS:
            yield Token("delimiter", bytes([c]), start)
            i += 1
            continue
        while i < len(data) and data[i] not in _SPACE + _DELIMITERS:
            i += 1
        yield Token("word", data[start:i], start)
