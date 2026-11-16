"""Создание TeX из разметки документов для встроенного Tectonic."""

from __future__ import annotations

import html.parser
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

from core.workers.atomic_output import atomic_output_path
from core.workers.engine_policy import adaptive_timeout

FONT_CHOICE = r"\IfFontExistsTF{Arial}{\setmainfont{Arial}}{\IfFontExistsTF{Segoe UI}{\setmainfont{Segoe UI}}{}}"


class TectonicUnavailableError(RuntimeError):
    """Движок или его общие ресурсы недоступны для всей очереди."""


def _bundled_cache_environment(executable: str, should_cancel=None) -> dict[str, str] | None:
    """Создаёт персональную копию подготовленного кэша из поставки."""
    seed = Path(executable).resolve().parent / "cache"
    marker = seed / ".multifora-cache-id"
    if not seed.is_dir():
        if getattr(sys, "frozen", False):
            raise TectonicUnavailableError("Установочный пакет Tectonic неполон: отсутствуют ресурсы")
        return None
    if not marker.is_file():
        raise TectonicUnavailableError("Установочный пакет Tectonic неполон: отсутствует описание ресурсов")
    try:
        cache_id = marker.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as error:
        raise TectonicUnavailableError(f"Не удалось прочитать описание ресурсов Tectonic: {error}") from error
    if not re.fullmatch(r"[0-9a-f]{64}", cache_id):
        raise TectonicUnavailableError("Установочный пакет Tectonic содержит неверное описание ресурсов")
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache") / "Multifora" / "tectonic"
    destination = base / cache_id

    def copy_resource(source, target):
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("Конвертация отменена пользователем")
        return shutil.copy2(source, target)

    try:
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("Конвертация отменена пользователем")
        base.mkdir(parents=True, exist_ok=True)
        installed_marker = destination / marker.name
        if installed_marker.is_file() and installed_marker.read_text(encoding="ascii").strip() != cache_id:
            raise TectonicUnavailableError("Описание установленного кэша Tectonic повреждено")
        if not installed_marker.is_file():
            with tempfile.TemporaryDirectory(prefix="cache-", dir=base) as staging:
                temporary = Path(staging) / "prepared"
                shutil.copytree(seed, temporary, copy_function=copy_resource)
                try:
                    os.rename(temporary, destination)
                except FileExistsError:
                    if not (destination / marker.name).is_file():
                        raise
    except InterruptedError:
        raise
    except (OSError, UnicodeError, shutil.Error) as error:
        if callable(should_cancel) and should_cancel():
            raise InterruptedError("Конвертация отменена пользователем") from error
        raise TectonicUnavailableError(f"Не удалось подготовить ресурсы Tectonic: {error}") from error
    environment = os.environ.copy()
    environment["TECTONIC_CACHE_DIR"] = str(destination)
    return environment


def _resource_failure(detail: str) -> bool:
    lower_detail = detail.lower()
    return any(
        marker in lower_detail
        for marker in (
            "failed to download",
            "failed to fetch",
            "network error",
            "failed to create directory",
            "permission denied",
            "no writable cache",
        )
    )


def _timeout_error(detail: str, timeout: int, *, bundled: bool) -> Exception:
    if _resource_failure(detail) or "downloading" in detail.lower():
        instruction = (
            "Проверьте доступ к папке данных приложения."
            if bundled
            else "Проверьте интернет и доступ к папке кэша Tectonic."
        )
        return TectonicUnavailableError(f"Tectonic не смог подготовить ресурсы за {timeout} секунд. {instruction}")
    return TimeoutError(f"Обработка документа Tectonic превысила {timeout} секунд")


def find_tectonic() -> str | None:
    roots = [Path(__file__).resolve().parents[3], Path(sys.executable).resolve().parent]
    if getattr(sys, "_MEIPASS", None):
        roots.append(Path(sys._MEIPASS))
    for root in roots:
        candidate = root / "bin" / "tectonic" / ("tectonic.exe" if os.name == "nt" else "tectonic")
        if candidate.is_file():
            return str(candidate)
    return shutil.which("tectonic")


def escape_tex(value: str) -> str:
    chars = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "%": r"\%",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\u00a0": "~",
    }
    return "".join(chars.get(char, char) for char in value)


class _Node:
    def __init__(self, tag="", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []


class _MarkupParser(html.parser.HTMLParser):
    void = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "pagebreak", "source", "wbr"}
    )

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.void:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def build_tex(layout, resource_dir: str | None = None) -> tuple[str, dict[str, bytes]]:
    parser = _MarkupParser()
    parser.feed(layout.markup)
    assets = dict(layout.assets)
    warnings = layout.warnings

    def asset(src):
        parsed = urlsplit(src or "")
        name = unquote(parsed.path)
        data = assets.get(name)
        if data is None and resource_dir and not parsed.scheme and not parsed.netloc and not os.path.isabs(name):
            base = Path(resource_dir).resolve()
            candidate = (base / name).resolve()
            if candidate.is_relative_to(base) and candidate.is_file():
                data = candidate.read_bytes()
        if data is None:
            warnings.add("не удалось прочитать изображение: " + (src or "без имени"))
            return ""
        suffix = Path(name).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".pdf"}:
            warnings.add("формат изображения не поддерживается Tectonic: " + suffix)
            return ""
        safe_name = f"asset{len(render_assets)}{suffix}"
        render_assets[safe_name] = data
        return safe_name

    def render(node):
        if isinstance(node, str):
            return escape_tex(node)
        tag = node.tag
        if tag in {"style", "script", "head", "title"}:
            if tag == "style":
                warnings.add("таблицы стилей HTML поддерживаются частично")
            return ""
        if tag == "img":
            name = asset(node.attrs.get("src"))
            if not name:
                return ""
            css = node.attrs.get("style") or ""
            dimensions = []
            for prop in ("width", "height"):
                match = re.search(rf"(?:^|;)\s*{prop}\s*:\s*([0-9.]+)(pt|cm|mm|in)\b", css, re.I)
                if match:
                    dimensions.append(f"{prop}={match.group(1)}{match.group(2).lower()}")
            dimensions.append("keepaspectratio")
            return r"\includegraphics[" + ",".join(dimensions) + "]{" + name + "}"
        if tag == "br":
            return r"\newline{}"
        if tag == "pagebreak":
            return "\\par\\newpage\n"
        if tag == "hr":
            return "\\par\\noindent\\rule{\\linewidth}{0.4pt}\\par\n"
        if tag == "table":

            def rows(current):
                for child in current.children:
                    if isinstance(child, _Node):
                        if child.tag == "tr":
                            yield child
                        elif child.tag in {"thead", "tbody", "tfoot"}:
                            yield from rows(child)

            table_rows = list(rows(node))
            count = max(
                (
                    len([cell for cell in row.children if isinstance(cell, _Node) and cell.tag in {"td", "th"}])
                    for row in table_rows
                ),
                default=1,
            )
            warnings.add("оформление и ширина таблиц могут отличаться")
            text = r"\begin{longtable}{" + "|".join(["p{" + f"{0.9 / count:.3f}" + r"\linewidth}"] * count) + "}\n"
            for row in table_rows:
                cells = [cell for cell in row.children if isinstance(cell, _Node) and cell.tag in {"td", "th"}]
                if any("colspan" in cell.attrs or "rowspan" in cell.attrs for cell in cells):
                    warnings.add("объединение ячеек таблиц может отличаться")
                text += " & ".join("".join(render(c) for c in cell.children) for cell in cells) + r" \\" + "\n"
            return text + "\\end{longtable}\n"
        content = "".join(render(child) for child in node.children)
        if tag in {"b", "strong"}:
            if "\\par" in content:
                return r"{\bfseries " + content + "}"
            return r"\textbf{" + content + "}"
        if tag in {"i", "em"}:
            if "\\par" in content:
                return r"{\itshape " + content + "}"
            return r"\textit{" + content + "}"
        if tag == "u":
            if "\\par" in content:
                warnings.add("подчёркивание нескольких абзацев не поддерживается")
                return content
            return r"\underline{" + content + "}"
        if tag in {"code", "pre"}:
            return r"\texttt{" + content + "}"
        if tag in {"ul", "ol"}:
            env = "itemize" if tag == "ul" else "enumerate"
            return f"\\begin{{{env}}}\n{content}\\end{{{env}}}\n"
        if tag == "li":
            return r"\item " + content + "\n"
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            content = r"\textbf{" + content + "}"
        css = node.attrs.get("style") or ""
        props = {
            key.strip().lower(): value.strip() if key.strip().lower() == "font-family" else value.strip().lower()
            for declaration in css.split(";")
            if ":" in declaration
            for key, value in [declaration.split(":", 1)]
        }
        leading = trailing = ""
        if tag == "span":
            leading_match = re.match(r"^\s+", content)
            trailing_match = re.search(r"\s+$", content)
            if leading_match:
                leading = " "
                content = content[leading_match.end() :]
            if trailing_match and content:
                content = content.rstrip()
                trailing = " "
        font = props.get("font-family", "")
        if font:
            if re.fullmatch(r"[\w .-]{1,80}", font) and "_" not in font:
                content = (
                    r"{\IfFontExistsTF{" + font + r"}{\fontspec{" + font + r"}}"
                    r"{\PackageWarning{Multifora}{MULTIFORA-MISSING-FONT:" + font + "}}" + content + "}"
                )
            else:
                warnings.add("имя шрифта не поддерживается")
        if props.get("font-weight") in {"bold", "700", "800", "900"}:
            content = (r"{\bfseries " if "\\par" in content else r"\textbf{") + content + "}"
        if props.get("font-style") == "italic":
            content = (r"{\itshape " if "\\par" in content else r"\textit{") + content + "}"
        if props.get("text-decoration") == "underline":
            if "\\par" in content:
                warnings.add("подчёркивание нескольких абзацев не поддерживается")
            else:
                content = r"\underline{" + content + "}"
        block_tag = tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6"}
        paragraph_font = ""
        size = re.fullmatch(r"([0-9.]+)pt", props.get("font-size", ""))
        if size and 1 <= float(size.group(1)) <= 200:
            points = float(size.group(1))
            leading_points = points * 1.2
            line_height = props.get("line-height", "")
            if re.fullmatch(r"[0-9.]+", line_height) and 0.5 <= float(line_height) <= 4:
                leading_points = points * float(line_height)
            elif re.fullmatch(r"[0-9.]+pt", line_height) and 1 <= float(line_height[:-2]) <= 300:
                leading_points = float(line_height[:-2])
            font_command = r"\fontsize{" + f"{points:g}" + "}{" + f"{leading_points:g}" + r"}\selectfont "
            if block_tag:
                paragraph_font = font_command
            else:
                content = "{" + font_command + content + "}"
        color = re.fullmatch(r"#([0-9a-f]{6})", props.get("color", ""))
        if color:
            if "\\par" in content:
                content = r"{\color[HTML]{" + color.group(1).upper() + "}" + content + "}"
            else:
                content = r"\textcolor[HTML]{" + color.group(1).upper() + "}{" + content + "}"
        align = props.get("text-align")
        if align in {"center", "right"}:
            content = (r"{\centering " if align == "center" else r"{\raggedleft ") + content + r"\par}"
        if tag == "span":
            content = leading + content + trailing
        ignored = set(props) - {
            "font-weight",
            "font-style",
            "text-decoration",
            "font-size",
            "font-family",
            "color",
            "text-align",
            "margin-left",
            "margin-right",
            "margin-top",
            "margin-bottom",
            "text-indent",
            "line-height",
        }
        if ignored:
            warnings.add("часть отступов и параметров расположения не поддерживается")
        if block_tag:

            def points(value):
                match = re.fullmatch(r"(-?[0-9.]+)pt", value or "")
                return float(match.group(1)) if match else 0.0

            before, after = points(props.get("margin-top")), points(props.get("margin-bottom"))
            left, right = points(props.get("margin-left")), points(props.get("margin-right"))
            indent = points(props.get("text-indent"))
            prefix = ""
            label = node.attrs.get("data-list-label")
            if label is not None:
                try:
                    left = float(node.attrs.get("data-list-left", "36"))
                    hanging = float(node.attrs.get("data-list-hanging", "18"))
                    if not 0 <= left <= 400 or not 0 <= hanging <= 400:
                        raise ValueError
                except ValueError:
                    left, hanging = 36, 18
                    warnings.add("отступ списка может отличаться")
                marker = r"\textbullet{}" if label == "•" else escape_tex(label)
                prefix = rf"\hspace*{{-{hanging:g}pt}}\makebox[{hanging:g}pt][l]{{{marker}}}"
            elif indent:
                prefix = rf"\hspace*{{{indent:g}pt}}"
            content = (
                (
                    "\\par\\ifdim\\pagetotal>0pt\\newpage\\fi\n"
                    if node.attrs.get("data-page-break-before") == "true"
                    else "\\par\n"
                )
                + (rf"\vspace*{{{before:g}pt}}" if before else "")
                + rf"{{\leftskip={left:g}pt\rightskip={right:g}pt\parindent=0pt "
                + paragraph_font
                + r"\spaceskip=.40em plus .15em minus .05em \noindent "
                + prefix
                + content
                + "\\par}"
                + (rf"\vspace*{{{after:g}pt}}" if after else "")
                + "\n"
            )
        return content

    render_assets: dict[str, bytes] = {}
    body = render(parser.root)
    left, top, right, bottom = layout.margins
    geometry = (
        f"paperwidth={layout.width:g}pt,paperheight={layout.height:g}pt,"
        f"left={left:g}pt,top={top:g}pt,right={right:g}pt,bottom={bottom:g}pt"
    )
    if (
        layout.width <= left + right
        or layout.height <= top + bottom
        or min(layout.width, layout.height, left, top, right, bottom) < 0
    ):
        raise ValueError("Некорректные размеры страницы или полей")
    source = (
        r"\documentclass{article}"
        "\n"
        r"\usepackage[" + geometry + r"]{geometry}"
        "\n"
        + r"\usepackage{fontspec,graphicx,xcolor,longtable}"
        + "\n"
        + FONT_CHOICE
        + "\n"
        + r"\setlength{\parindent}{0pt}"
        "\n" + r"\pagestyle{empty}"
        "\n"
        r"\begin{document}"
        "\n" + body + "\n" + r"\end{document}"
        "\n"
    )
    return source, render_assets


def render_pdf(layout, destination: str, should_cancel, resource_dir: str | None = None, *, status=None) -> None:
    executable = find_tectonic()
    if not executable:
        raise TectonicUnavailableError("Не найден встроенный движок Tectonic")
    if callable(status) and (Path(executable).resolve().parent / "cache").is_dir():
        status("Подготовка установленных ресурсов Tectonic...")
    if should_cancel():
        raise InterruptedError("Конвертация отменена пользователем")
    environment = _bundled_cache_environment(executable, should_cancel)
    source, assets = build_tex(layout, resource_dir)
    timeout = adaptive_timeout(len(source.encode("utf-8")) + sum(map(len, assets.values())))
    try:
        temporary_directory = tempfile.TemporaryDirectory(prefix="multifora_tex_")
    except OSError as error:
        raise TectonicUnavailableError(f"Не удалось создать временную папку Tectonic: {error}") from error
    with temporary_directory as directory:
        directory_path = Path(directory)
        tex = directory_path / "document.tex"
        log_path = directory_path / "tectonic.log.txt"
        try:
            tex.write_text(source, encoding="utf-8")
            for name, data in assets.items():
                (directory_path / name).write_bytes(data)
            log_file = log_path.open("wb")
        except OSError as error:
            raise TectonicUnavailableError(f"Не удалось подготовить временные файлы Tectonic: {error}") from error
        with log_file as log:
            process = subprocess.Popen(
                [
                    executable,
                    "--untrusted",
                    "--print",
                    *(["--only-cached"] if environment else []),
                    "--outdir",
                    directory,
                    str(tex),
                ],
                cwd=directory,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            start = time.monotonic()
            next_notice = 5
            try:
                while process.poll() is None:
                    if should_cancel():
                        raise InterruptedError("Конвертация отменена пользователем")
                    elapsed = time.monotonic() - start
                    if callable(status) and elapsed >= next_notice:
                        message = (
                            "Tectonic обрабатывает документ."
                            if environment
                            else "При первом запуске Tectonic загружает необходимые файлы."
                        )
                        status(f"Создание PDF: прошло {int(elapsed)} с. {message}")
                        next_notice += 15
                    if elapsed > timeout:
                        log.flush()
                        detail = log_path.read_text(encoding="utf-8", errors="replace")
                        raise _timeout_error(detail, timeout, bundled=environment is not None)
                    time.sleep(0.1)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        output = directory_path / "document.pdf"
        if log_path.is_file():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            for font_name in set(re.findall(r"MULTIFORA-MISSING-FONT:([^\r\n}]+)", log_text)):
                layout.warnings.add(f"шрифт {font_name.strip()} недоступен и был заменён")
        if process.returncode or not output.is_file() or output.stat().st_size == 0:
            full_detail = log_text
            detail = full_detail[-1000:].strip()
            if _resource_failure(full_detail):
                instruction = (
                    "Проверьте доступ к папке данных и переустановите приложение. "
                    if environment
                    else "Проверьте интернет и доступ к кэшу. "
                )
                raise TectonicUnavailableError("Tectonic не смог получить необходимые файлы. " + instruction + detail)
            raise RuntimeError("Tectonic не создал PDF" + (f": {detail}" if detail else ""))
        if should_cancel():
            raise InterruptedError("Конвертация отменена пользователем")
        with atomic_output_path(destination) as temporary:
            shutil.copyfile(output, temporary)
