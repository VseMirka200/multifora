from __future__ import annotations

import datetime as _dt
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


_METADATA_GROUPS = frozenset(
    {
        "author",
        "title",
        "subject",
        "keywords",
        "comments",
        "dates",
        "application",
        "custom",
    }
)


class MetadataMixin:
    """Удаление метаданных из поддерживаемых форматов документов."""

    _DOCX_CORE_FIELDS = {
        "author": {"creator", "lastModifiedBy"},
        "title": {"title"},
        "subject": {"subject"},
        "keywords": {"keywords"},
        "comments": {"description", "category", "contentStatus"},
        "dates": {"created", "modified"},
    }
    _DOCX_APP_FIELDS = {
        "application": {"Application", "AppVersion", "Template", "TotalTime"},
        "custom": {"Company", "Manager", "HyperlinkBase"},
    }
    _ODT_FIELDS = {
        "author": {"creator", "initial-creator", "printed-by"},
        "title": {"title"},
        "subject": {"subject"},
        "keywords": {"keyword"},
        "comments": {"description"},
        "dates": {"creation-date", "date", "print-date"},
        "application": {"generator", "editing-duration", "editing-cycles", "document-statistic"},
        "custom": {"user-defined"},
    }
    _PDF_INFO_FIELDS = {
        "author": {"author"},
        "title": {"title"},
        "subject": {"subject"},
        "keywords": {"keywords"},
        "comments": set(),
        "dates": {"creationDate", "modDate"},
        "application": {"creator", "producer"},
    }

    def _remove_metadata_files(self):
        updated_files = []
        total = len(self.files)
        selected_groups = set(getattr(self, "metadata_fields", set()) or set())
        remove_all = bool(getattr(self, "metadata_remove_all", False))

        if not remove_all:
            selected_groups &= _METADATA_GROUPS

        for index, file_item in enumerate(self.files, start=1):
            if self._should_cancel():
                break

            path = str(getattr(file_item, "path", "") or "")
            self.status.emit(f"Удаление метаданных: {os.path.basename(path)}")
            try:
                self._remove_metadata_from_path(path, remove_all, selected_groups)
                updated_files.append((file_item, path))
            except Exception as error:
                self._record_error(file_item, str(error))

            if total:
                self.progress.emit(int(index * 100 / total))

        self._emit_finished(updated_files=updated_files)

    def _remove_metadata_from_path(self, path: str, remove_all: bool, selected_groups: set[str]):
        extension = Path(path).suffix.lower()
        if extension == ".pdf":
            return self._remove_pdf_metadata(path, remove_all, selected_groups)
        if extension == ".docx":
            return self._remove_docx_metadata(path, remove_all, selected_groups)
        if extension == ".odt":
            return self._remove_odt_metadata(path, remove_all, selected_groups)
        if extension == ".doc":
            return self._remove_doc_metadata_via_word(path, remove_all, selected_groups)
        raise ValueError("Поддерживаются только PDF, DOCX, ODT и DOC (через Microsoft Word).")

    @staticmethod
    def _temporary_path(path: str) -> str:
        folder = os.path.dirname(os.path.abspath(path)) or None
        suffix = os.path.splitext(path)[1]
        handle = tempfile.NamedTemporaryFile(prefix=".multifora_meta_", suffix=suffix, dir=folder, delete=False)
        handle.close()
        return handle.name

    def _remove_pdf_metadata(self, path: str, remove_all: bool, selected_groups: set[str]):
        try:
            import pymupdf as fitz
        except Exception as error:  # pragma: no cover - dependency error is environment-specific
            raise RuntimeError(f"PyMuPDF недоступен: {error}") from error

        document = fitz.open(path)
        temp_path = self._temporary_path(path)
        try:
            metadata = dict(document.metadata or {})
            if remove_all:
                metadata = {}
            else:
                for group in selected_groups:
                    for key in self._PDF_INFO_FIELDS.get(group, set()):
                        if key in metadata:
                            metadata[key] = ""
            document.set_metadata(metadata)

            if remove_all:
                delete_xml = getattr(document, "del_xml_metadata", None)
                if callable(delete_xml):
                    delete_xml()
            else:
                self._remove_selected_pdf_xmp(document, selected_groups)

            document.save(temp_path, garbage=4, clean=True, deflate=True)
            document.close()
            document = None
            os.replace(temp_path, path)
        finally:
            if document is not None:
                document.close()
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _remove_selected_pdf_xmp(self, document, selected_groups: set[str]):
        get_xml = getattr(document, "get_xml_metadata", None)
        set_xml = getattr(document, "set_xml_metadata", None)
        if not callable(get_xml) or not callable(set_xml):
            return
        xml_text = get_xml() or ""
        if not xml_text.strip():
            return

        if "custom" in selected_groups:
            # Пользовательские XMP-поля невозможно надежно перечислить заранее.
            # Удаляем XMP-пакет целиком, затем стандартные неснятые поля остаются
            # доступными из PDF Info dictionary.
            delete_xml = getattr(document, "del_xml_metadata", None)
            if callable(delete_xml):
                delete_xml()
                return

        ns = {
            "dc": "http://purl.org/dc/elements/1.1/",
            "pdf": "http://ns.adobe.com/pdf/1.3/",
            "xmp": "http://ns.adobe.com/xap/1.0/",
        }
        targets = set()
        if "author" in selected_groups:
            targets.add(f"{{{ns['dc']}}}creator")
        if "title" in selected_groups:
            targets.add(f"{{{ns['dc']}}}title")
        if "subject" in selected_groups:
            targets.add(f"{{{ns['dc']}}}description")
        if "keywords" in selected_groups:
            targets.update({f"{{{ns['dc']}}}subject", f"{{{ns['pdf']}}}Keywords"})
        if "dates" in selected_groups:
            targets.update(
                {
                    f"{{{ns['xmp']}}}CreateDate",
                    f"{{{ns['xmp']}}}ModifyDate",
                    f"{{{ns['xmp']}}}MetadataDate",
                }
            )
        if "application" in selected_groups:
            targets.update({f"{{{ns['xmp']}}}CreatorTool", f"{{{ns['pdf']}}}Producer"})
        if not targets:
            return

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return

        changed = False
        for parent in root.iter():
            for child in list(parent):
                if child.tag in targets:
                    parent.remove(child)
                    changed = True
            for attr_name in list(parent.attrib):
                if attr_name in targets:
                    del parent.attrib[attr_name]
                    changed = True
        if changed:
            set_xml(ET.tostring(root, encoding="unicode"))

    def _remove_docx_metadata(self, path: str, remove_all: bool, selected_groups: set[str]):
        temp_path = self._temporary_path(path)
        try:
            with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
                for info in source.infolist():
                    name = info.filename
                    data = source.read(name)

                    if remove_all and name in {"docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"}:
                        continue
                    if remove_all and name == "_rels/.rels":
                        data = self._docx_remove_property_relationships(data, remove_core=True, remove_app=True, remove_custom=True)
                    elif remove_all and name == "[Content_Types].xml":
                        data = self._docx_remove_property_content_types(data, remove_core=True, remove_app=True, remove_custom=True)
                    elif not remove_all:
                        if name == "docProps/core.xml":
                            data = self._docx_filter_core_properties(data, selected_groups)
                        elif name == "docProps/app.xml":
                            data = self._docx_filter_app_properties(data, selected_groups)
                        elif name == "docProps/custom.xml" and "custom" in selected_groups:
                            continue
                        elif name == "_rels/.rels" and "custom" in selected_groups:
                            data = self._docx_remove_property_relationships(data, remove_custom=True)
                        elif name == "[Content_Types].xml" and "custom" in selected_groups:
                            data = self._docx_remove_property_content_types(data, remove_custom=True)

                    target.writestr(info, data)
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _docx_filter_core_properties(self, data: bytes, groups: set[str]) -> bytes:
        root = ET.fromstring(data)
        local_names = set()
        for group in groups:
            local_names.update(self._DOCX_CORE_FIELDS.get(group, set()))
        if not local_names:
            return data
        for child in list(root):
            if self._local_name(child.tag) in local_names:
                root.remove(child)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _docx_filter_app_properties(self, data: bytes, groups: set[str]) -> bytes:
        root = ET.fromstring(data)
        local_names = set()
        for group in groups:
            local_names.update(self._DOCX_APP_FIELDS.get(group, set()))
        if not local_names:
            return data
        for child in list(root):
            if self._local_name(child.tag) in local_names:
                root.remove(child)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _docx_remove_property_relationships(
        self,
        data: bytes,
        *,
        remove_core: bool = False,
        remove_app: bool = False,
        remove_custom: bool = False,
    ) -> bytes:
        root = ET.fromstring(data)
        targets = set()
        if remove_core:
            targets.add("docProps/core.xml")
        if remove_app:
            targets.add("docProps/app.xml")
        if remove_custom:
            targets.add("docProps/custom.xml")
        for child in list(root):
            target = str(child.attrib.get("Target", "")).lstrip("/")
            if target in targets:
                root.remove(child)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _docx_remove_property_content_types(
        self,
        data: bytes,
        *,
        remove_core: bool = False,
        remove_app: bool = False,
        remove_custom: bool = False,
    ) -> bytes:
        root = ET.fromstring(data)
        targets = set()
        if remove_core:
            targets.add("/docProps/core.xml")
        if remove_app:
            targets.add("/docProps/app.xml")
        if remove_custom:
            targets.add("/docProps/custom.xml")
        for child in list(root):
            if child.attrib.get("PartName") in targets:
                root.remove(child)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _remove_odt_metadata(self, path: str, remove_all: bool, selected_groups: set[str]):
        temp_path = self._temporary_path(path)
        try:
            with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "meta.xml":
                        data = self._filter_odt_meta_xml(data, remove_all, selected_groups)
                    target.writestr(info, data)
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _filter_odt_meta_xml(self, data: bytes, remove_all: bool, groups: set[str]) -> bytes:
        root = ET.fromstring(data)
        office_meta = None
        for element in root.iter():
            if self._local_name(element.tag) == "meta":
                office_meta = element
                break
        if office_meta is None:
            return data
        if remove_all:
            for child in list(office_meta):
                office_meta.remove(child)
        else:
            local_names = set()
            for group in groups:
                local_names.update(self._ODT_FIELDS.get(group, set()))
            for child in list(office_meta):
                if self._local_name(child.tag) in local_names:
                    office_meta.remove(child)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _remove_doc_metadata_via_word(self, path: str, remove_all: bool, selected_groups: set[str]):
        if os.name != "nt":
            raise RuntimeError("Удаление метаданных из DOC доступно только в Windows через Microsoft Word.")
        try:
            import win32com.client
        except Exception as error:  # pragma: no cover - Windows-only
            raise RuntimeError(f"Microsoft Word automation недоступна: {error}") from error

        property_ids = {
            "author": (3, 7),
            "title": (1,),
            "subject": (2,),
            "keywords": (4,),
            "comments": (5, 18, 26, 27),
            "dates": (10, 11, 12),
            "application": (6, 8, 9, 13),
            "custom": (20, 21, 28, 29),
        }
        groups = _METADATA_GROUPS if remove_all else selected_groups
        word = None
        document = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            document = word.Documents.Open(os.path.abspath(path), ReadOnly=False, AddToRecentFiles=False)
            builtins = document.BuiltInDocumentProperties
            for group in groups:
                for property_id in property_ids.get(group, ()):
                    try:
                        prop = builtins.Item(property_id)
                        current = prop.Value
                        if isinstance(current, bool):
                            prop.Value = False
                        elif isinstance(current, (int, float)):
                            prop.Value = 0
                        elif isinstance(current, _dt.datetime):
                            # Встроенные даты OLE нельзя удалить, поэтому заменяем их нейтральной эпохой.
                            prop.Value = _dt.datetime(1980, 1, 1)
                        else:
                            prop.Value = ""
                    except Exception:
                        pass
            if remove_all or "custom" in groups:
                try:
                    custom = document.CustomDocumentProperties
                    for index in range(custom.Count, 0, -1):
                        try:
                            custom.Item(index).Delete()
                        except Exception:
                            pass
                except Exception:
                    pass
            document.Save()
        except Exception as error:
            raise RuntimeError(f"Не удалось очистить DOC через Microsoft Word: {error}") from error
        finally:  # pragma: no cover - Windows-only
            if document is not None:
                try:
                    document.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass

    @staticmethod
    def _local_name(tag: str) -> str:
        return str(tag).rsplit("}", 1)[-1]
