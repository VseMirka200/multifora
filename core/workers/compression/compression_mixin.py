import os
import subprocess
import time

from app.core.app_utils import _debug_log
import app.core.deps as deps
from app.core.models import FileItem


class CompressionMixin:
    def _compress_image_files(self):
        total = len(self.files)
        results = []

        for i, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self._emit_finished(results, [])
                return
            try:
                if file.is_file and file.file_type == "image":
                    ext = os.path.splitext(file.name)[1].lower()
                    compressed_path = file.path.rsplit(".", 1)[0] + "_compressed" + ext
                    compressed_path = self._get_unique_path(compressed_path)

                    if deps.HAS_PIL:
                        try:
                            with deps.Image.open(file.path) as img:
                                if img.mode in ("RGBA", "LA", "P"):
                                    rgb_img = deps.Image.new("RGB", img.size, (255, 255, 255))
                                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                                    img = rgb_img

                                if ext in [".jpg", ".jpeg"]:
                                    img.save(
                                        compressed_path,
                                        "JPEG",
                                        quality=self.compression_level,
                                        optimize=True,
                                        progressive=True,
                                    )
                                elif ext == ".png":
                                    img.save(
                                        compressed_path,
                                        "PNG",
                                        optimize=True,
                                        compress_level=min(9, int(self.compression_level / 10)),
                                    )
                                else:
                                    img.save(compressed_path)

                                original_size = os.path.getsize(file.path)
                                compressed_size = os.path.getsize(compressed_path)

                                if compressed_size < original_size:
                                    results.append(FileItem(compressed_path))
                                    ratio = (1 - compressed_size / original_size) * 100
                                    self.status.emit(f"Изображение сжато: -{ratio:.1f}%")
                                else:
                                    os.remove(compressed_path)
                                    self.status.emit("Изображение уже оптимизировано")

                        except Exception as img_error:
                            msg = f"Ошибка сжатия {file.name}: {img_error}"
                            self._record_error(file, msg)
                            self.error.emit(msg)
                    else:
                        msg = "Для сжатия изображений установите Pillow: pip install Pillow"
                        self._record_error(file, msg)
                        self.error.emit(msg)
                else:
                    msg = f"Файл {file.name} не является изображением или не поддерживается"
                    self._record_error(file, msg)
                    self.error.emit(msg)

            except Exception as e:
                msg = f"Ошибка сжатия {file.name}: {str(e)}"
                self._record_error(file, msg)
                self.error.emit(msg)

            self.progress.emit(int((i + 1) / total * 100))
            self.status.emit(f"Сжатие: {file.name}")

        self._emit_finished(results, [])

    def _compress_image_files_with_replace_support(self):
        total = len(self.files)
        results = []
        updated = []

        for i, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self._emit_finished(results, updated)
                return
            try:
                if file.is_file and file.file_type == "image":
                    ext = os.path.splitext(file.name)[1].lower()
                    compressed_path = file.path.rsplit(".", 1)[0] + "_compressed" + ext
                    compressed_path = self._get_unique_path(compressed_path)

                    if deps.HAS_PIL:
                        try:
                            with deps.Image.open(file.path) as img:
                                if img.mode in ("RGBA", "LA", "P"):
                                    rgb_img = deps.Image.new("RGB", img.size, (255, 255, 255))
                                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                                    img = rgb_img

                                if ext in [".jpg", ".jpeg"]:
                                    img.save(
                                        compressed_path,
                                        "JPEG",
                                        quality=self.compression_level,
                                        optimize=True,
                                        progressive=True,
                                    )
                                elif ext == ".png":
                                    img.save(
                                        compressed_path,
                                        "PNG",
                                        optimize=True,
                                        compress_level=min(9, int(self.compression_level / 10)),
                                    )
                                else:
                                    img.save(compressed_path)

                                original_size = os.path.getsize(file.path)
                                compressed_size = os.path.getsize(compressed_path)

                                if compressed_size < original_size:
                                    ratio = (1 - compressed_size / original_size) * 100
                                    if getattr(self, "replace_image", False):
                                        try:
                                            os.replace(compressed_path, file.path)
                                            updated.append((file, file.path))
                                            self.status.emit(
                                                f"Изображение сжато и заменено: {file.name} (-{ratio:.1f}%)"
                                            )
                                        except Exception as replace_error:
                                            msg = f"Ошибка замены {file.name}: {replace_error}"
                                            self._record_error(file, msg)
                                            self.error.emit(msg)
                                            try:
                                                os.remove(compressed_path)
                                            except Exception:
                                                pass
                                    else:
                                        results.append(FileItem(compressed_path))
                                        self.status.emit(f"Изображение сжато: {file.name} (-{ratio:.1f}%)")
                                else:
                                    os.remove(compressed_path)
                                    self.status.emit(f"Изображение уже оптимизировано: {file.name}")

                        except Exception as img_error:
                            msg = f"Ошибка сжатия {file.name}: {img_error}"
                            self._record_error(file, msg)
                            self.error.emit(msg)
                    else:
                        msg = "Для сжатия изображений установите Pillow: pip install Pillow"
                        self._record_error(file, msg)
                        self.error.emit(msg)
                else:
                    msg = f"Файл {file.name} не является изображением или не поддерживается"
                    self._record_error(file, msg)
                    self.error.emit(msg)

            except Exception as e:
                msg = f"Ошибка сжатия {file.name}: {str(e)}"
                self._record_error(file, msg)
                self.error.emit(msg)

            self.progress.emit(int((i + 1) / total * 100))
            self.status.emit(f"Сжатие: {file.name}")

        self._emit_finished(results, updated)

    def _compress_pdf_files(self):
        deps.ensure_ghostscript_detected()
        _debug_log(f"Начало сжатия PDF: {len(self.files)} файлов")
        total = len(self.files)
        results = []
        updated = []
        self._last_pdf_error = ""

        for i, file in enumerate(self.files):
            if self._should_cancel():
                self.status.emit("Операция отменена пользователем")
                self._emit_finished(results, updated)
                return
            try:
                if not (file.is_file and file.path.lower().endswith(".pdf")):
                    continue

                original_size = os.path.getsize(file.path)
                compressed_path = self._get_unique_path(file.path.rsplit(".", 1)[0] + "_compressed.pdf")

                success = False
                compression_method = ""
                compression_ratio = 0.0

                if deps.HAS_GHOSTSCRIPT:
                    success, compression_method, compression_ratio = self._compress_pdf_with_ghostscript(
                        file.path, compressed_path
                    )
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    if os.path.exists(compressed_path):
                        try:
                            os.remove(compressed_path)
                        except Exception:
                            pass
                    self._emit_finished(results, updated)
                    return

                if not success and deps.HAS_PYMUPDF:
                    success, compression_method, compression_ratio = self._compress_pdf_with_pymupdf(
                        file.path, compressed_path
                    )
                if self._should_cancel():
                    self.status.emit("Операция отменена пользователем")
                    if os.path.exists(compressed_path):
                        try:
                            os.remove(compressed_path)
                        except Exception:
                            pass
                    self._emit_finished(results, updated)
                    return

                if success and os.path.exists(compressed_path):
                    new_size = os.path.getsize(compressed_path)

                    if new_size < original_size:
                        if getattr(self, "replace_pdf", False):
                            try:
                                os.replace(compressed_path, file.path)
                                updated.append((file, file.path))
                                ratio = (1 - new_size / original_size) * 100
                                self.status.emit(f"PDF сжат и заменен ({compression_method}): {file.name} (-{ratio:.1f}%)")
                            except Exception as e:
                                msg = f"Ошибка замены PDF {file.name}: {str(e)}"
                                self._record_error(file, msg)
                                self.error.emit(msg)
                                try:
                                    os.remove(compressed_path)
                                except Exception:
                                    pass
                        else:
                            results.append(FileItem(compressed_path))
                            ratio = (1 - new_size / original_size) * 100
                            self.status.emit(f"PDF сжат ({compression_method}): {file.name} (-{ratio:.1f}%)")
                    else:
                        try:
                            os.remove(compressed_path)
                        except Exception as e:
                            _debug_log(f"Не удалось удалить временный PDF: {e}")
                        self.status.emit(f"PDF уже оптимизирован: {file.name}")

                else:
                    if not self._last_pdf_error:
                        if os.path.exists(compressed_path):
                            try:
                                out_size = os.path.getsize(compressed_path)
                                if out_size == 0:
                                    self._last_pdf_error = "сжатый файл пустой"
                                elif out_size >= original_size:
                                    self._last_pdf_error = "уже оптимизирован"
                            except Exception:
                                self._last_pdf_error = "не удалось проверить результат"
                        else:
                            self._last_pdf_error = "выходной файл не создан"
                    if self._last_pdf_error == "уже оптимизирован":
                        self.status.emit(f"PDF уже оптимален: {file.name}")
                    else:
                        reason = f" ({self._last_pdf_error})" if self._last_pdf_error else ""
                        self.status.emit(f"Не удалось сжать PDF: {file.name}{reason}")
                    if os.path.exists(compressed_path):
                        try:
                            os.remove(compressed_path)
                        except Exception:
                            pass
                    self._last_pdf_error = ""

            except Exception as e:
                msg = f"Ошибка PDF: {str(e)[:100]}"
                self._record_error(file, msg)
                self.error.emit(msg)

            self.progress.emit(int((i + 1) / total * 100))

        self._emit_finished(results, updated)

    def _compress_pdf_with_ghostscript(self, input_path: str, output_path: str) -> tuple[bool, str, float]:
        if self._should_cancel():
            self._last_pdf_error = "отменено пользователем"
            return False, "", 0.0
        try:
            original_size = os.path.getsize(input_path)
            settings = self._get_ghostscript_settings()

            cmd = [
                deps.GHOSTSCRIPT_PATH,
                "-dNOPAUSE",
                "-dBATCH",
                "-dSAFER",
                "-sDEVICE=pdfwrite",
                f"-dPDFSETTINGS={settings['pdf_settings']}",
                f"-dCompatibilityLevel={settings['compatibility_level']}",
                f"-dEmbedAllFonts={settings['embed_fonts']}",
                f"-dSubsetFonts={settings['subset_fonts']}",
                f"-dAutoRotatePages={settings['auto_rotate']}",
                f"-dColorImageDownsampleType={settings['image_downsample_type']}",
                f"-dColorImageResolution={settings['color_resolution']}",
                f"-dGrayImageDownsampleType={settings['image_downsample_type']}",
                f"-dGrayImageResolution={settings['gray_resolution']}",
                f"-dMonoImageDownsampleType={settings['image_downsample_type']}",
                f"-dMonoImageResolution={settings['mono_resolution']}",
                f"-dColorConversionStrategy={settings['color_strategy']}",
                f"-dConvertCMYKImagesToRGB={settings['convert_cmyk_to_rgb']}",
                f"-dJPEGQ={settings['jpeg_quality']}",
                "-dOptimize=true",
                "-dUseFlateCompression=true",
                f"-sOutputFile={output_path}",
                input_path,
            ]

            _debug_log(f"Запуск Ghostscript: {' '.join(cmd[:10])}...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            start = time.time()
            timeout = 120
            while True:
                if self._should_cancel():
                    try:
                        process.terminate()
                        process.wait(timeout=2)
                    except Exception:
                        try:
                            process.kill()
                        except Exception:
                            pass
                    self._last_pdf_error = "отменено пользователем"
                    return False, "", 0.0
                if process.poll() is not None:
                    break
                if time.time() - start > timeout:
                    try:
                        process.kill()
                    except Exception:
                        pass
                    self._last_pdf_error = "время сжатия истекло"
                    return False, "", 0.0
                time.sleep(0.1)

            stdout, stderr = process.communicate()
            result_returncode = process.returncode

            if result_returncode == 0:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    new_size = os.path.getsize(output_path)
                    ratio = (1 - new_size / original_size) * 100
                    if new_size < original_size:
                        method_name = self._get_compression_method_name(settings)
                        return True, f"Ghostscript ({method_name})", ratio
                    return False, "", 0.0
                _debug_log("Ghostscript создал пустой файл")
                self._last_pdf_error = "Ghostscript создал пустой файл"
                return False, "", 0.0

            err = (stderr or "").strip()[:500]
            _debug_log(f"Ghostscript ошибка: {err}")
            self._last_pdf_error = f"Ghostscript: {err}" if err else "Ghostscript: неизвестная ошибка"
            return False, "", 0.0

        except Exception as e:
            _debug_log(f"Ошибка Ghostscript: {e}")
            self._last_pdf_error = f"Ghostscript: {e}"
            return False, "", 0.0

    def _compress_pdf_with_pymupdf(self, input_path: str, output_path: str) -> tuple[bool, str, float]:
        if self._should_cancel():
            self._last_pdf_error = "отменено пользователем"
            return False, "", 0.0
        try:
            import fitz

            original_size = os.path.getsize(input_path)
            doc = fitz.open(input_path)
            if self._should_cancel():
                doc.close()
                self._last_pdf_error = "отменено пользователем"
                return False, "", 0.0

            if self.pdf_method == "max":
                garbage = 4
                deflate = True
                clean = True
                method_name = "PyMuPDF (макс. сжатие)"
            elif self.pdf_method == "quality":
                garbage = 3
                deflate = True
                clean = True
                method_name = "PyMuPDF (качество)"
            elif self.pdf_method == "optimize":
                garbage = 4
                deflate = True
                clean = True
                method_name = "PyMuPDF (оптимизация)"
            else:
                garbage = 4
                deflate = True
                clean = True
                method_name = "PyMuPDF (авто)"

            doc.save(output_path, garbage=garbage, deflate=deflate, clean=clean)
            doc.close()

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                new_size = os.path.getsize(output_path)
                ratio = (1 - new_size / original_size) * 100
                if new_size < original_size:
                    return True, method_name, ratio
                return False, "", 0.0

            self._last_pdf_error = "PyMuPDF создал пустой файл"
            return False, "", 0.0

        except Exception as e:
            _debug_log(f"Ошибка PyMuPDF: {e}")
            self._last_pdf_error = f"PyMuPDF: {e}"
            return False, "", 0.0

    def _get_ghostscript_settings(self):
        if self.pdf_method == "max":
            return {
                "pdf_settings": "/screen",
                "compatibility_level": "1.4",
                "embed_fonts": "true",
                "subset_fonts": "true",
                "auto_rotate": "/None",
                "image_downsample_type": "/Average",
                "color_resolution": 72,
                "gray_resolution": 72,
                "mono_resolution": 150,
                "color_strategy": "/sRGB",
                "convert_cmyk_to_rgb": "true",
                "jpeg_quality": 40,
                "optimize": True,
                "method_name": "Максимальное сжатие",
            }
        if self.pdf_method == "quality":
            return {
                "pdf_settings": "/prepress",
                "compatibility_level": "1.5",
                "embed_fonts": "true",
                "subset_fonts": "true",
                "auto_rotate": "/PageByPage",
                "image_downsample_type": "/Bicubic",
                "color_resolution": 300,
                "gray_resolution": 300,
                "mono_resolution": 1200,
                "color_strategy": "/LeaveColorUnchanged",
                "convert_cmyk_to_rgb": "false",
                "jpeg_quality": 92,
                "optimize": True,
                "method_name": "Сохранить качество",
            }
        if self.pdf_method == "optimize":
            return {
                "pdf_settings": "/printer",
                "compatibility_level": "1.4",
                "embed_fonts": "true",
                "subset_fonts": "true",
                "auto_rotate": "/None",
                "image_downsample_type": "/Bicubic",
                "color_resolution": 300,
                "gray_resolution": 300,
                "mono_resolution": 1200,
                "color_strategy": "/sRGB",
                "convert_cmyk_to_rgb": "true",
                "jpeg_quality": 90,
                "optimize": True,
                "method_name": "Только оптимизация",
            }

        if self.files and len(self.files) > 0:
            file_size = os.path.getsize(self.files[0].path)
            if file_size > 10 * 1024 * 1024:
                return {
                    "pdf_settings": "/ebook",
                    "compatibility_level": "1.4",
                    "embed_fonts": "true",
                    "subset_fonts": "true",
                    "auto_rotate": "/PageByPage",
                    "image_downsample_type": "/Bicubic",
                    "color_resolution": 150,
                    "gray_resolution": 150,
                    "mono_resolution": 300,
                    "color_strategy": "/sRGB",
                    "convert_cmyk_to_rgb": "true",
                    "jpeg_quality": 75,
                    "optimize": True,
                    "method_name": "Авто (для больших файлов)",
                }
            return {
                "pdf_settings": "/printer",
                "compatibility_level": "1.4",
                "embed_fonts": "true",
                "subset_fonts": "true",
                "auto_rotate": "/None",
                "image_downsample_type": "/Bicubic",
                "color_resolution": 300,
                "gray_resolution": 300,
                "mono_resolution": 1200,
                "color_strategy": "/sRGB",
                "convert_cmyk_to_rgb": "true",
                "jpeg_quality": 85,
                "optimize": True,
                "method_name": "Авто (стандарт)",
            }

        return {
            "pdf_settings": "/printer",
            "compatibility_level": "1.4",
            "embed_fonts": "true",
            "subset_fonts": "true",
            "auto_rotate": "/None",
            "image_downsample_type": "/Bicubic",
            "color_resolution": 300,
            "gray_resolution": 300,
            "mono_resolution": 1200,
            "color_strategy": "/sRGB",
            "convert_cmyk_to_rgb": "true",
            "jpeg_quality": 85,
            "optimize": True,
            "method_name": "Стандарт",
        }

    def _get_compression_method_name(self, settings):
        return settings.get("method_name", "Стандарт")
