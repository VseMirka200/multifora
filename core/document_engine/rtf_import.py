"""Read the main text, inline styling, tables, and pictures of RTF."""

import base64
import codecs
import re
from dataclasses import dataclass, replace
from pathlib import Path

from lxml import etree
from striprtf.striprtf import destinations

_TOKEN = re.compile(
    r"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\([^a-zA-Z])|([{}])|([^{}\\]+)",
)
_SKIPPED = set(destinations) | {"fonttbl", "colortbl", "stylesheet"}


@dataclass
class _State:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    skip: bool = False
    unicode_skip: int = 1
    picture: list | None = None
    picture_type: str | None = None
    in_table: bool = False


class _Document:
    def __init__(self):
        self.body = etree.Element("body")
        self.paragraph = None
        self.table = None
        self.row = None
        self.cell = None

    def current_paragraph(self, state):
        if state.in_table and self.row is not None:
            if self.cell is None:
                self.cell = etree.SubElement(self.row, "td")
            parent = self.cell
        else:
            parent = self.body
            self.table = None
        if self.paragraph is None or self.paragraph.getparent() is not parent:
            self.paragraph = etree.SubElement(parent, "p", style="white-space: pre-wrap")
        return self.paragraph

    def text(self, value, state):
        if not value:
            return
        target = self.current_paragraph(state)
        for active, tag in ((state.bold, "strong"), (state.italic, "em"), (state.underline, "u")):
            if active:
                target = etree.SubElement(target, tag)
        if len(target):
            target[-1].tail = (target[-1].tail or "") + value
        else:
            target.text = (target.text or "") + value

    def picture(self, state, parent_state):
        if state.picture_type and state.picture:
            picture = bytes.fromhex("".join(state.picture))
            data = base64.b64encode(picture).decode("ascii")
            paragraph = self.current_paragraph(parent_state)
            etree.SubElement(paragraph, "img", src=f"data:image/{state.picture_type};base64,{data}")

    def start_row(self):
        if self.table is None:
            self.table = etree.SubElement(self.body, "table")
        self.row = etree.SubElement(self.table, "tr")
        self.cell = self.paragraph = None


def read_body(source, should_cancel):
    if should_cancel():
        raise InterruptedError("Конвертация отменена")
    rtf = Path(source).read_bytes().decode("latin-1").lstrip()
    if not rtf.startswith(r"{\rtf"):
        raise ValueError("Некорректный документ RTF")
    document = _Document()
    encoding = "cp1252"
    stack = []
    state = _State()
    skip = position = 0
    pending_hex = bytearray()
    high_surrogate = None

    def emit(value):
        nonlocal skip, high_surrogate
        if skip:
            consumed = min(skip, len(value))
            value = value[consumed:]
            skip -= consumed
            if not value:
                return
        if high_surrogate is not None:
            value = (high_surrogate + value).encode("utf-16", "surrogatepass").decode("utf-16", "replace")
            high_surrogate = None
        if not state.skip:
            document.text(value, state)

    while position < len(rtf):
        if should_cancel():
            raise InterruptedError("Конвертация отменена")
        match = _TOKEN.match(rtf, position)
        if not match:
            raise ValueError("Некорректный управляющий символ RTF")
        position = match.end()
        word, argument, hex_byte, symbol, brace, literal = match.groups()
        if pending_hex and hex_byte is None:
            document.text(pending_hex.decode(encoding, errors="replace"), state)
            pending_hex.clear()
        if brace == "{":
            if len(stack) >= 256:
                raise ValueError("Слишком много вложенных групп RTF")
            stack.append(state)
            state = replace(state)
        elif brace == "}":
            if not stack:
                raise ValueError("Некорректная группа RTF")
            parent = stack.pop()
            if state.picture is not None and state.picture is not parent.picture:
                document.picture(state, parent)
            if not stack:
                break
            state = parent
        elif word == "bin":
            length = int(argument or "0")
            if length < 0 or position + length > len(rtf):
                raise ValueError("Некорректный двоичный блок RTF")
            if state.picture is not None:
                state.picture.append(rtf[position:position + length].encode("latin-1").hex())
            position += length
        elif state.picture is not None:
            if word in {"pngblip", "jpegblip"}:
                state.picture_type = "png" if word == "pngblip" else "jpeg"
            elif literal:
                state.picture.append(literal)
        elif state.skip:
            continue
        elif word == "pict":
            state.picture = []
        elif symbol == "*" or word in _SKIPPED:
            state.skip = True
        elif word == "ansicpg":
            encoding = f"cp{argument}"
            codecs.lookup(encoding)
        elif word == "uc":
            state.unicode_skip = max(0, int(argument or "1"))
        elif word == "u":
            number = int(argument or "0") & 0xFFFF
            skip = 0
            if 0xD800 <= number <= 0xDBFF:
                if high_surrogate is not None:
                    emit("")
                high_surrogate = chr(number)
            else:
                emit(chr(number) if high_surrogate is not None or not 0xDC00 <= number <= 0xDFFF else "\ufffd")
            skip = state.unicode_skip
        elif word in {"b", "i", "ul", "ulnone", "plain"}:
            flag = argument != "0"
            if word in {"b", "plain"}:
                state.bold = flag and word != "plain"
            if word in {"i", "plain"}:
                state.italic = flag and word != "plain"
            if word in {"ul", "ulnone", "plain"}:
                state.underline = flag and word == "ul"
        elif word == "par":
            document.current_paragraph(state)
            document.paragraph = None
        elif word == "trowd":
            document.start_row()
            state.in_table = True
        elif word == "intbl":
            state.in_table = argument != "0"
        elif word == "cell":
            document.current_paragraph(state)
            document.cell = document.paragraph = None
        elif word == "row":
            document.row = document.cell = document.paragraph = None
            state.in_table = False
        elif word in {"pard", "page", "sect"}:
            state.in_table = False
            document.paragraph = None
        elif word in {"line", "tab", "emdash", "endash", "bullet"}:
            emit({"line": "\n", "tab": "\t", "emdash": "—", "endash": "–", "bullet": "•"}[word])
        elif hex_byte is not None:
            if skip:
                skip -= 1
            else:
                pending_hex.append(int(hex_byte, 16))
        elif symbol in {"{", "}", "\\", "~", "_", "-"}:
            emit({"~": "\u00a0", "_": "\u2011", "-": "\u00ad"}.get(symbol, symbol))
        elif literal:
            value = literal.replace("\r", "").replace("\n", "")
            if skip:
                consumed = min(len(value), skip)
                value = value[consumed:]
                skip -= consumed
            if value:
                emit(value.encode("latin-1").decode(encoding, errors="replace"))
    if stack:
        raise ValueError("Незакрытая группа RTF")
    return document.body
