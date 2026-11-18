"""Parse PDF primitive objects from an object-syntax token sequence.

Indirect objects, streams and cross-reference tables are handled separately.
"""

import math
import re
from dataclasses import dataclass

from core.pdf_engine.lexer import tokenize


@dataclass(frozen=True)
class Name:
    value: bytes


@dataclass(frozen=True)
class Reference:
    object_number: int
    generation: int


_INTEGER = re.compile(rb"[+-]?\d+\Z")
_REAL = re.compile(rb"[+-]?(?:\d+\.\d*|\.\d+)\Z")


def parse_object(data: bytes):
    """Parse exactly one PDF object, rejecting trailing tokens and invalid syntax."""
    tokens = list(tokenize(data))
    index = 0

    def parse(depth=0):
        nonlocal index
        if depth > 100:
            raise ValueError("PDF object nesting limit exceeded")
        if index >= len(tokens):
            raise ValueError("Unexpected end of PDF object")
        token = tokens[index]
        index += 1
        if token.kind == "string":
            return token.value
        if token.kind == "name":
            return Name(token.value)
        if token.value == b"[" and token.kind == "delimiter":
            result = []
            while index < len(tokens) and tokens[index].value != b"]":
                result.append(parse(depth + 1))
            if index == len(tokens):
                raise ValueError("Unterminated PDF array")
            index += 1
            return result
        if token.value == b"<<" and token.kind == "delimiter":
            result = {}
            while index < len(tokens) and tokens[index].value != b">>":
                key = tokens[index]
                if key.kind != "name":
                    raise ValueError("PDF dictionary key must be a name")
                index += 1
                result[key.value] = parse(depth + 1)
            if index == len(tokens):
                raise ValueError("Unterminated PDF dictionary")
            index += 1
            return result
        if token.kind != "word":
            raise ValueError("Unexpected PDF delimiter")
        if token.value in (b"true", b"false", b"null"):
            return {b"true": True, b"false": False, b"null": None}[token.value]
        if _INTEGER.fullmatch(token.value):
            number = int(token.value)
            if index + 1 < len(tokens):
                generation, marker = tokens[index:index + 2]
                if (
                    generation.kind == marker.kind == "word"
                    and _INTEGER.fullmatch(generation.value)
                    and marker.value == b"R"
                ):
                    gen = int(generation.value)
                    if number <= 0 or not 0 <= gen <= 65535:
                        raise ValueError("Invalid PDF reference")
                    index += 2
                    return Reference(number, gen)
            return number
        if _REAL.fullmatch(token.value):
            return float(token.value)
        raise ValueError("Invalid PDF object token")

    result = parse()
    if index != len(tokens):
        raise ValueError("Trailing tokens after PDF object")
    return result


def serialize_object(value, *, _depth=0):
    """Serialize a primitive PDF object without writing a complete PDF file."""
    if _depth > 100:
        raise ValueError("PDF object nesting limit exceeded")
    if value is None:
        return b"null"
    if isinstance(value, bool):
        return b"true" if value else b"false"
    if isinstance(value, int):
        return str(value).encode("ascii")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("PDF numbers must be finite")
        # PDF numbers do not support exponent notation.
        from decimal import Decimal

        return format(Decimal(str(value)), "f").encode("ascii")
    if isinstance(value, bytes):
        return b"<" + value.hex().encode("ascii") + b">"
    if isinstance(value, Name):
        result = bytearray(b"/")
        for byte in value.value:
            if 33 <= byte <= 126 and byte not in b"#%()/<>[]{}":
                result.append(byte)
            else:
                result.extend(f"#{byte:02X}".encode("ascii"))
        return bytes(result)
    if isinstance(value, Reference):
        if value.object_number <= 0 or not 0 <= value.generation <= 65535:
            raise ValueError("Invalid PDF reference")
        return f"{value.object_number} {value.generation} R".encode("ascii")
    if isinstance(value, (list, tuple)):
        return b"[" + b" ".join(serialize_object(item, _depth=_depth + 1) for item in value) + b"]"
    if isinstance(value, dict):
        items = []
        for key, item in value.items():
            if not isinstance(key, bytes):
                raise TypeError("PDF dictionary keys must be bytes")
            items.append(serialize_object(Name(key), _depth=_depth + 1))
            items.append(serialize_object(item, _depth=_depth + 1))
        return b"<< " + b" ".join(items) + b" >>"
    raise TypeError(f"Unsupported PDF object type: {type(value).__name__}")
