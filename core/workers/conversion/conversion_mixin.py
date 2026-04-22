import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.app_utils import _debug_log
from app.core.deps import (
    HAS_ODF_PYTHON,
    HAS_PDF_TO_IMAGE,
    HAS_PDF_TO_WORD,
    HAS_PIL,
    HAS_PYMUPDF,
    HAS_WORD_TO_PDF,
    Image,
    OpenDocumentText,
    convert_from_path,
    load,
    pdf2docx,
    teletype,
    text,
    word_to_pdf,
)
from app.core.models import FileItem

_WORD_WARMUP_LOCK = threading.Lock()
_WORD_WARMUP_DONE = False


def prewarm_word_background(status_callback=None, log_callback=None) -> bool:
    """Запускает фоновую подготовку Microsoft Word один раз за сессию."""
    global _WORD_WARMUP_DONE
    if os.name != "nt" or not HAS_WORD_TO_PDF:
        return False
    if _WORD_WARMUP_DONE:
        return False

    with _WORD_WARMUP_LOCK:
        if _WORD_WARMUP_DONE:
            return False
        try:
            if callable(status_callback):
                status_callback("Фоновая подготовка Microsoft Word...")
            import pythoncom
            import win32com.client as win32

            pythoncom.CoInitialize()
            word_app = None
            try:
                word_app = win32.DispatchEx("Word.Application")
                word_app.Visible = False
                word_app.DisplayAlerts = 0
                _WORD_WARMUP_DONE = True
                return True
            finally:
                if word_app is not None:
                    try:
                        word_app.Quit()
                    except Exception:
                        pass
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
        except Exception as e:
            msg = f"Не удалось запустить фоновую подготовку Microsoft Word: {e}"
            if callable(log_callback):
                try:
                    log_callback(msg)
                except Exception:
                    _debug_log(msg)
            else:
                _debug_log(msg)
            return False


class ConversionMixin:
    @staticmethod
    def _normalize_word_com_path(path: str) -> str:
        value = str(path or "").strip().strip('"')
        if not value:
            return value
        if value.lower().startswith("file:///"):
            value = value[8:]
        value = urllib.parse.unquote(value)
        if value.startswith("/") and len(value) >= 3 and value[2] == ":":
            value = value[1:]
        value = value.replace("/", "\\")
        return os.path.normpath(value)

    def _resolve_python_for_docx2pdf(self) -> str | None:
        """Return a Python interpreter path suitable for `python -c` calls."""
        candidates = []
        try:
            base_exe = getattr(sys, "_base_executable", None)
            if base_exe:
                candidates.append(base_exe)
        except Exception:
            pass
        candidates.append(sys.executable)
        candidates.append(shutil.which("python"))
        candidates.append(shutil.which("python3"))

        for exe in candidates:
            if not exe:
                continue
            if os.path.basename(exe).lower().startswith("python"):
                return exe
        return None

    def _convert_files(self):
        total = len(self.files)
        results = []
        # Для самых тяжелых сценариев используем отдельные batch-пути.
        if self.conversion_type == "word_to_pdf":
            results = self._convert_word_to_pdf_batch()
            self.finished.emit({"new_files": results, "updated_files": [], "errors": self.errors})
            return
        if self.conversion_type == "pdf_to_word":
            results = self._convert_pdf_to_word_batch()
            self.finished.emit({"new_files": results, "updated_files": [], "errors": self.errors})
            return

        for i, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self.finished.emit({"new_files": results, "updated_files": [], "errors": self.errors})
                return
            if not file.is_file:
                continue

            self.status.emit(f"Конвертация: {file.name}")
            try:
                converted_path = None

                if self.conversion_type == "word_to_pdf":
                    converted_path = self._convert_word_to_pdf(file)
                elif self.conversion_type == "pdf_to_word":
                    converted_path = self._convert_pdf_to_word(file)
                elif self.conversion_type == "word_to_odt":
                    converted_path = self._convert_word_to_odt(file)
                elif self.conversion_type == "odt_to_word":
                    converted_path = self._convert_odt_to_word(file)
                elif self.conversion_type == "odt_to_pdf":
                    converted_path = self._convert_odt_to_pdf(file)
                elif self.conversion_type == "pdf_to_odt":
                    converted_path = self._convert_pdf_to_odt(file)
                elif self.conversion_type in ("pdf_to_image", "pdf_to_images"):
                    converted_path = self._convert_pdf_to_image(file)
                elif self.conversion_type == "image_to_pdf":
                    converted_path = self._convert_image_to_pdf(file)

                if converted_path and os.path.exists(converted_path):
                    results.append(FileItem(converted_path))

            except Exception as e:
                msg = f"Ошибка конвертации файла {file.name}: {str(e)}"
                self._record_error(file, msg)
                self.error.emit(msg)

            self.progress.emit(int((i + 1) / total * 100))

        self.finished.emit({"new_files": results, "updated_files": [], "errors": self.errors})

    def _convert_word_to_pdf_batch(self) -> list[FileItem]:
        """Быстрый пакетный DOC/DOCX -> PDF через один скрытый экземпляр Word."""
        total = len(self.files)
        results: list[FileItem] = []
        if total == 0:
            return results

        if os.name != "nt":
            for i, file in enumerate(self.files):
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    break
                if not file.is_file:
                    continue
                self.status.emit(f"Конвертация: {file.name}")
                try:
                    converted_path = self._convert_word_to_pdf(file)
                    if converted_path and os.path.exists(converted_path):
                        results.append(FileItem(converted_path))
                except Exception as e:
                    msg = f"Ошибка конвертации файла {file.name}: {str(e)}"
                    self._record_error(file, msg)
                    self.error.emit(msg)
                self.progress.emit(int((i + 1) / total * 100))
            return results

        try:
            import pythoncom
            import win32com.client as win32
        except Exception as e:
            msg = f"Скрытая конвертация Word недоступна (нужен pywin32): {e}"
            self._record_error(None, msg)
            self.error.emit(msg)
            return results

        self._warmup_word()
        word_app = None
        pythoncom.CoInitialize()
        try:
            # Один COM-экземпляр Word на всю пачку файлов заметно ускоряет конвертацию.
            word_app = win32.DispatchEx("Word.Application")
            word_app.Visible = False
            word_app.DisplayAlerts = 0

            for i, file in enumerate(self.files):
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    break
                if not file.is_file:
                    continue
                self.status.emit(f"Конвертация: {file.name}")
                try:
                    if not file.path.lower().endswith((".doc", ".docx")):
                        raise Exception("Поддерживаются только DOC/DOCX")

                    pdf_path = file.path.rsplit(".", 1)[0] + ".pdf"
                    pdf_path = self._get_unique_path(pdf_path)
                    normalized_src = self._normalize_word_com_path(file.path)
                    normalized_dst = self._normalize_word_com_path(pdf_path)
                    if not os.path.exists(normalized_src):
                        raise FileNotFoundError(f"Файл не найден: {normalized_src}")

                    document = None
                    try:
                        # Каждый файл открывается только на время экспорта и сразу закрывается.
                        document = word_app.Documents.Open(
                            normalized_src,
                            ConfirmConversions=False,
                            ReadOnly=True,
                            AddToRecentFiles=False,
                            Revert=False,
                            Visible=False,
                            OpenAndRepair=True,
                        )
                        document.ExportAsFixedFormat(
                            OutputFileName=normalized_dst,
                            ExportFormat=17,  # wdExportFormatPDF
                            OpenAfterExport=False,
                        )
                    finally:
                        if document is not None:
                            try:
                                document.Close(False)
                            except Exception:
                                pass

                    if os.path.exists(normalized_dst):
                        results.append(FileItem(normalized_dst))
                    else:
                        raise Exception("Word не создал выходной PDF-файл")
                except Exception as e:
                    msg = f"Ошибка конвертации файла {file.name}: {str(e)}"
                    self._record_error(file, msg)
                    self.error.emit(msg)
                self.progress.emit(int((i + 1) / total * 100))
        finally:
            if word_app is not None:
                try:
                    word_app.Quit()
                except Exception:
                    pass
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

        return results

    def _convert_pdf_to_word_batch(self) -> list[FileItem]:
        files = [f for f in self.files if getattr(f, "is_file", False)]
        total = len(files)
        results: list[FileItem] = []
        if total == 0:
            return results

        if not HAS_PDF_TO_WORD:
            msg = "Установите pdf2docx"
            self._record_error(None, msg)
            self.error.emit(msg)
            return results

        max_workers = min(4, max(1, ((os.cpu_count() or 2) // 2)))
        if total <= 1 or max_workers == 1:
            for i, file in enumerate(files):
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    break
                self.status.emit(f"Конвертация: {file.name}")
                try:
                    converted_path = self._convert_pdf_to_word(file)
                    if converted_path and os.path.exists(converted_path):
                        results.append(FileItem(converted_path))
                except Exception as e:
                    msg = f"Ошибка конвертации файла {file.name}: {str(e)}"
                    self._record_error(file, msg)
                    self.error.emit(msg)
                self.progress.emit(int((i + 1) / total * 100))
            return results

        processed = 0
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pdf2docx") as executor:
            future_map = {}
            for file in files:
                if file.path.lower().endswith(".pdf"):
                    future_map[executor.submit(self._convert_pdf_to_word, file)] = file
                else:
                    processed += 1
                    self.progress.emit(int(processed / total * 100))

            for future in as_completed(future_map):
                file = future_map[future]
                if self._should_cancel():
                    for pending in future_map:
                        pending.cancel()
                    self.status.emit("Операция отменена пользователем")
                    break
                self.status.emit(f"Конвертация: {file.name}")
                try:
                    converted_path = future.result()
                    if converted_path and os.path.exists(converted_path):
                        results.append(FileItem(converted_path))
                    else:
                        raise Exception("pdf2docx не создал выходной DOCX-файл")
                except Exception as e:
                    msg = f"Ошибка конвертации файла {file.name}: {str(e)}"
                    self._record_error(file, msg)
                    self.error.emit(msg)
                finally:
                    processed += 1
                    self.progress.emit(int(processed / total * 100))

        return results

    def _warmup_word(self):
        if self._word_warmup_done:
            return
        if os.name != "nt" or not HAS_WORD_TO_PDF:
            self._word_warmup_done = True
            return
        try:
            started = prewarm_word_background(
                status_callback=self.status.emit if callable(getattr(self, "status", None)) else None,
                log_callback=_debug_log,
            )
            if started:
                time.sleep(0.6)
        except Exception as e:
            _debug_log(f"Не удалось подготовить Microsoft Word: {e}")
        finally:
            self._word_warmup_done = True

    def _convert_word_to_pdf(self, file: FileItem) -> str:
        if file.path.lower().endswith((".doc", ".docx")):
            pdf_path = file.path.rsplit(".", 1)[0] + ".pdf"
            pdf_path = self._get_unique_path(pdf_path)

            if HAS_WORD_TO_PDF:
                try:
                    self._warmup_word()
                    if self._should_cancel():
                        raise Exception("Конвертация отменена пользователем")

                    # Скрытая конвертация через отдельный экземпляр Word: окно не всплывает.
                    try:
                        if self._convert_word_to_pdf_hidden_com(file.path, pdf_path):
                            if self._should_cancel():
                                raise Exception("Конвертация отменена пользователем")
                            return pdf_path
                    except Exception as com_error:
                        raise Exception(f"Скрытая COM-конвертация недоступна: {com_error}")
                except Exception as e:
                    err_text = str(e)
                    if ("NoneType" in err_text and "write" in err_text) or ("could not start Microsoft Word" in err_text):
                        err_text = (
                            "Не удалось запустить Microsoft Word. Убедитесь, что Word установлен и активирован, "
                            "хотя бы один раз запускался вручную и не осталось зависших процессов WINWORD.EXE."
                        )
                    if "Скрытая COM-конвертация недоступна" in err_text:
                        err_text = (
                            "Скрытая конвертация Word недоступна (нужен pywin32 и рабочий COM Word). "
                            f"Детали: {err_text}"
                        )
                    raise Exception(f"Ошибка конвертации Word в PDF: {err_text}")
            else:
                raise Exception(
                    "docx2pdf не установлен или Microsoft Word недоступен. "
                    "Установите docx2pdf и проверьте запуск Word."
                )

        return None

    def _convert_word_to_pdf_hidden_com(self, src_path: str, dst_pdf_path: str) -> bool:
        if os.name != "nt":
            return False
        try:
            import pythoncom
            import win32com.client as win32
        except Exception:
            return False

        word_app = None
        document = None
        normalized_src = self._normalize_word_com_path(src_path)
        normalized_dst = self._normalize_word_com_path(dst_pdf_path)
        if not os.path.exists(normalized_src):
            raise FileNotFoundError(f"Файл не найден: {normalized_src}")
        pythoncom.CoInitialize()
        try:
            word_app = win32.DispatchEx("Word.Application")
            word_app.Visible = False
            word_app.DisplayAlerts = 0

            document = word_app.Documents.Open(
                normalized_src,
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
                Revert=False,
                Visible=False,
                OpenAndRepair=True,
            )
            document.ExportAsFixedFormat(
                OutputFileName=normalized_dst,
                ExportFormat=17,  # wdExportFormatPDF
                OpenAfterExport=False,
            )
            return os.path.exists(normalized_dst)
        finally:
            if document is not None:
                try:
                    document.Close(False)
                except Exception:
                    pass
            if word_app is not None:
                try:
                    word_app.Quit()
                except Exception:
                    pass
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def _convert_pdf_to_word(self, file: FileItem) -> str:
        if file.path.lower().endswith(".pdf"):
            docx_path = file.path.rsplit(".", 1)[0] + ".docx"
            docx_path = self._get_unique_path(docx_path)

            if HAS_PDF_TO_WORD:
                try:
                    converter = pdf2docx.Converter(file.path)
                    converter.convert(docx_path)
                    converter.close()
                    return docx_path
                except Exception as e:
                    raise Exception(f"Ошибка конвертации PDF в Word: {e}")
            else:
                raise Exception("Установите pdf2docx")

        return None

    def _convert_word_to_odt(self, file: FileItem) -> str:
        if file.path.lower().endswith((".doc", ".docx")):
            if not HAS_ODF_PYTHON:
                raise Exception("Установите odfpy для конвертации ODT")
            try:
                import docx

                doc = docx.Document(file.path)
                odt_doc = OpenDocumentText()
                for para in doc.paragraphs:
                    p = text.P(text=para.text)
                    odt_doc.text.addElement(p)
                odt_path = file.path.rsplit(".", 1)[0] + ".odt"
                odt_path = self._get_unique_path(odt_path)
                odt_doc.save(odt_path)
                return odt_path
            except Exception as e:
                raise Exception(f"Ошибка конвертации Word в ODT: {e}")
        return None

    def _convert_odt_to_word(self, file: FileItem) -> str:
        if file.path.lower().endswith(".odt"):
            if not HAS_ODF_PYTHON:
                raise Exception("Установите odfpy для конвертации ODT")
            try:
                import docx

                odt_doc = load(file.path)
                docx_doc = docx.Document()
                for elem in odt_doc.getElementsByType(text.P):
                    txt = teletype.extractText(elem)
                    if txt and txt.strip():
                        docx_doc.add_paragraph(txt)
                docx_path = file.path.rsplit(".", 1)[0] + ".docx"
                docx_path = self._get_unique_path(docx_path)
                docx_doc.save(docx_path)
                return docx_path
            except Exception as e:
                raise Exception(f"Ошибка конвертации ODT в DOCX: {e}")
        return None

    def _convert_odt_to_pdf(self, file: FileItem) -> str:
        if file.path.lower().endswith(".odt"):
            docx_path = self._convert_odt_to_word(file)
            if not docx_path or not os.path.exists(docx_path):
                raise Exception("Не удалось создать DOCX из ODT")
            return self._convert_word_to_pdf(FileItem(docx_path))
        return None

    def _convert_pdf_to_odt(self, file: FileItem) -> str:
        if file.path.lower().endswith(".pdf"):
            docx_path = self._convert_pdf_to_word(file)
            if not docx_path or not os.path.exists(docx_path):
                raise Exception("Не удалось создать DOCX из PDF")
            return self._convert_word_to_odt(FileItem(docx_path))
        return None

    def _convert_pdf_to_image(self, file: FileItem) -> str:
        if file.path.lower().endswith(".pdf"):
            image_path = file.path.rsplit(".", 1)[0] + ".jpg"
            image_path = self._get_unique_path(image_path)

            if HAS_PDF_TO_IMAGE:
                try:
                    images = convert_from_path(file.path, dpi=200, first_page=1, last_page=1)
                    if images:
                        images[0].save(image_path, "JPEG", quality=90)
                        return image_path
                except Exception as e:
                    if HAS_PYMUPDF:
                        try:
                            import fitz

                            pdf_document = fitz.open(file.path)
                            page = pdf_document.load_page(0)
                            pix = page.get_pixmap()
                            pix.save(image_path)
                            pdf_document.close()
                            return image_path
                        except Exception as pymupdf_error:
                            raise Exception(f"Ошибка PyMuPDF: {pymupdf_error}")
                    raise Exception(f"Ошибка конвертации PDF в изображение: {e}")
            elif HAS_PYMUPDF:
                try:
                    import fitz

                    pdf_document = fitz.open(file.path)
                    page = pdf_document.load_page(0)
                    pix = page.get_pixmap()
                    pix.save(image_path)
                    pdf_document.close()
                    return image_path
                except Exception as e:
                    raise Exception(f"Ошибка PyMuPDF: {e}")
            else:
                raise Exception("Установите pdf2image или PyMuPDF: pip install pdf2image или pip install PyMuPDF")

        return None

    def _convert_image_to_pdf(self, file: FileItem) -> str:
        if file.path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")):
            pdf_path = file.path.rsplit(".", 1)[0] + ".pdf"
            pdf_path = self._get_unique_path(pdf_path)

            if HAS_PIL:
                try:
                    with Image.open(file.path) as img:
                        if img.mode in ("RGBA", "LA", "P"):
                            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                            rgb_img.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                            img = rgb_img

                        img.save(pdf_path, "PDF", resolution=100.0)
                        return pdf_path
                except Exception as e:
                    raise Exception(f"Ошибка конвертации изображения в PDF: {e}")
            elif HAS_PYMUPDF:
                try:
                    import fitz

                    doc = fitz.open()
                    img = fitz.open(file.path)
                    rect = fitz.Rect(0, 0, img[0].rect.width, img[0].rect.height)
                    page = doc.new_page(width=rect.width, height=rect.height)
                    page.insert_image(rect, filename=file.path)
                    doc.save(pdf_path)
                    doc.close()
                    img.close()
                    return pdf_path
                except Exception as e:
                    raise Exception(f"Ошибка PyMuPDF при конвертации в PDF: {e}")
            else:
                raise Exception("Установите Pillow или PyMuPDF: pip install Pillow или pip install PyMuPDF")

        return None
