"""Qt workers calling Craft CLI executables."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from core.craft_bridge import bridge, CraftError
from core.craft_routes import route_for_path
from core.conversion_formats import suffix_for_format
from core.file_models import FileItem
from core.filesystem import atomic_output_path, conversion_directory, get_unique_path, converted_name, compressed_name, normalized_path_key
from core.operation_requests import ConversionRequest, CompressionRequest, MergeRequest
from core.operation_result import CompressionSize
from .operation_worker import OperationWorker

class Cancelled(Exception):
    pass

class CraftWorker(OperationWorker):
    def __init__(self, request, sources):
        super().__init__()
        self.request = request
        self._prepare_operation(request.kind, sources)

    def _operation_handlers(self):
        return {"convert": self._batch, "compress": self._batch, "merge": self._merge}

    def _check_cancel(self):
        if self._should_cancel():
            raise Cancelled()

    def _call(self, engine, op, **kwargs):
        self._check_cancel()
        result = bridge.call(engine, op, **kwargs)
        self._check_cancel()
        return result

    def _produce(self, dest, engine, op, *, item=None, **kwargs):
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        with atomic_output_path(dest) as tmp:
            # Some engines refuse existing targets. The reserved file is empty and owned by this job.
            result = self._call(engine, op, output=tmp, **kwargs)
            if isinstance(result, dict):
                warnings = result.get("warnings") or result.get("importWarnings") or result.get("diagnostics")
                if warnings:
                    self._record_warning(item, str(warnings))
        return FileItem(dest)

    def _convert_one(self, item, req, new_files):
        selected = route_for_path(item.path, req.target_format)
        if selected is None:
            raise CraftError(f"Нет маршрута {Path(item.path).suffix} → {req.target_format}")
        folder = conversion_directory(item.folder, req.output_mode, req.output_dir)
        extension = suffix_for_format(req.target_format)
        if not extension:
            raise CraftError("Неизвестный выходной формат")
        if selected.operation == "render_pages":
            count = self._call(selected.engine, "page_count", input=item.path)["pages"]
            if not isinstance(count, int) or count <= 0:
                raise CraftError("Нет страниц для экспорта")
            for i in range(count):
                self._check_cancel()
                stem = Path(item.name).stem
                name = f"{stem}_{i+1:04d}{extension}" if count > 1 else stem + extension
                dest = get_unique_path(os.path.join(folder, name))
                self.status.emit(f"{item.name}: {i+1}/{count}")
                if selected.engine == "pdfcraft" and extension in (".webp", ".bmp"):
                    with tempfile.TemporaryDirectory(prefix="multifora-page-") as temp:
                        png = os.path.join(temp,"page.png")
                        self._call("pdfcraft","render",input=item.path,output=png,page=i)
                        new_files.append(self._produce(dest,"photocraft","convert",item=item,input=png))
                else:
                    new_files.append(self._produce(dest,selected.engine,"render",item=item,input=item.path,page=i))
                if req.sample:
                    break
            return
        dest = get_unique_path(os.path.join(folder, converted_name(item.name, extension)))
        new_files.append(self._produce(dest,selected.engine,selected.operation,item=item,input=item.path))

    def _compress_one(self, item, req, new_files, updated_files):
        is_pdf = req.compression_type == "pdf"
        engine = "pdfcraft" if is_pdf else "photocraft"
        extension = Path(item.path).suffix.lower()
        if is_pdf and extension != ".pdf":
            raise CraftError("Ожидается PDF")
        if not is_pdf and extension not in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
            raise CraftError("Сжатие доступно для JPEG, PNG, WebP и TIFF")
        options = {"method": req.pdf_method} if is_pdf else ({"quality": req.level} if extension in {".jpg", ".jpeg", ".webp"} else {})
        replace = req.replace_pdf if is_pdf else req.image_output_mode == "replace"
        folder = req.image_output_dir if not is_pdf and req.image_output_mode == "custom" else item.folder
        os.makedirs(folder, exist_ok=True)
        source_stat = os.stat(item.path)
        dest = item.path if replace else get_unique_path(os.path.join(folder,compressed_name(item.name,extension)))
        with tempfile.TemporaryDirectory(prefix=".multifora-compress-",dir=folder) as temp:
            candidate = os.path.join(temp, "output" + extension)
            result = self._call(engine,"compress",input=item.path,output=candidate,**options)
            after = os.path.getsize(candidate)
            if after <= 0:
                raise CraftError("Движок вернул пустой файл")
            if after >= source_stat.st_size:
                self._record_warning(item,"Файл не стал меньше; оригинал сохранён.")
                self.compression_sizes.append(CompressionSize(item.path,source_stat.st_size,source_stat.st_size))
                return
            self._check_cancel()
            if replace:
                current = os.stat(item.path)
                if (current.st_size,current.st_mtime_ns,current.st_ino) != (source_stat.st_size,source_stat.st_mtime_ns,source_stat.st_ino):
                    raise CraftError("Исходник изменился во время обработки; замена отменена")
                os.replace(candidate,item.path)
                updated_files.append((item,item.path))
            else:
                from core.filesystem import publish_new_file
                publish_new_file(candidate,dest)
                new_files.append(FileItem(dest))
            if isinstance(result,dict) and (result.get("warnings") or result.get("diagnostics")):
                self._record_warning(item,str(result.get("warnings") or result.get("diagnostics")))
            self.compression_sizes.append(CompressionSize(dest,source_stat.st_size,after))

    def _batch(self):
        new_files, updated_files = [], []
        for i,item in enumerate(self.files):
            if self._should_cancel():
                break
            self.status.emit(f"{i+1}/{len(self.files)}: {item.name}")
            try:
                if isinstance(self.request,ConversionRequest):
                    self._convert_one(item,self.request,new_files)
                else:
                    self._compress_one(item,self.request,new_files,updated_files)
            except Cancelled:
                break
            except Exception as exc:
                self._record_error(item,str(exc),cause=exc)
            self.progress.emit(int((i+1)*100/max(1,len(self.files))))
            if getattr(self.request,"sample",False):
                break
        self._emit_finished(new_files,updated_files)

    def _merge(self):
        req = self.request
        try:
            if any(normalized_path_key(f.path)==normalized_path_key(req.output_path) for f in self.files):
                raise CraftError("Результат не может заменить исходный файл")
            if req.output_format.lower() == "docx":
                if req.page_order or any(Path(f.path).suffix.lower() != ".docx" for f in self.files):
                    raise CraftError("Объединение в DOCX принимает только целые документы")
                result = self._produce(req.output_path,"wordcraft","merge",inputs=[f.path for f in self.files])
                self.progress.emit(100)
                self._emit_finished([result],[])
                return
            if req.output_format.lower() != "pdf":
                raise CraftError("Неизвестный формат объединения")
            with tempfile.TemporaryDirectory(prefix="multifora-merge-") as temp:
                paths=[]
                for i,item in enumerate(self.files):
                    self.status.emit(f"Подготовка {item.name}")
                    if Path(item.path).suffix.lower() == ".pdf":
                        paths.append(item.path)
                    elif Path(item.path).suffix.lower() == ".docx":
                        p=os.path.join(temp,f"document-{i+1}.pdf")
                        self._call("wordcraft","convert",input=item.path,output=p)
                        paths.append(p)
                    else:
                        raise CraftError("Объединение поддерживает PDF и DOCX → PDF")
                    self.progress.emit(int((i+1)*70/max(1,len(self.files))))
                self.status.emit("Объединение страниц…")
                result=self._produce(req.output_path,"pdfcraft","merge",inputs=paths,page_order=req.page_order)
            self.progress.emit(100)
            self._emit_finished([result],[])
        except Cancelled:
            self._emit_finished([],[])
