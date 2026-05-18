from PyQt6.QtCore import QThread, pyqtSignal

from .compression import CompressionMixin
from .conversion import ConversionMixin
from .merge import MergeMixin
from .operations import FileOpsMixin


class FileWorker(FileOpsMixin, ConversionMixin, CompressionMixin, MergeMixin, QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.operation = None
        self.files = []
        self.destination = ""
        self.conversion_type = ""
        self.conversion_format = ""
        self.new_names = []
        self.compression_level = 85
        self.compression_type = "image"
        self.pdf_method = "auto"
        self.replace_pdf = False
        self.replace_image = False
        self.merge_output_format = "pdf"
        self.merge_output_path = ""
        self._last_pdf_error = ""
        self._cancel_requested = False
        self.errors = []
        self._word_warmup_done = False

    def request_cancel(self):
        self._cancel_requested = True

    def _should_cancel(self) -> bool:
        return self._cancel_requested

    def _record_error(self, file_item, message: str):
        entry = {"message": message}
        if file_item is not None:
            entry["path"] = getattr(file_item, "path", None)
            entry["name"] = getattr(file_item, "name", None)
        self.errors.append(entry)

    def set_copy_move(self, files: list, destination: str, move: bool = False):
        self.operation = "move" if move else "copy"
        self.files = files
        self.destination = destination
        self._cancel_requested = False
        self.errors = []

    def set_conversion(self, files: list, conversion_type: str, conversion_format: str = ""):
        self.operation = "convert"
        self.files = files
        self.conversion_type = conversion_type
        self.conversion_format = conversion_format
        self._cancel_requested = False
        self.errors = []
        self._word_warmup_done = False

    def set_rename(self, files: list, new_names: list):
        self.operation = "rename"
        self.files = files
        self.new_names = new_names
        self._cancel_requested = False
        self.errors = []

    def set_compression(
        self,
        files: list,
        compression_level: int,
        compression_type: str = "image",
        pdf_method: str = "auto",
        replace_pdf: bool = False,
        replace_image: bool = False,
    ):
        self.operation = "compress"
        self.files = files
        self.compression_level = compression_level
        self.compression_type = compression_type
        self.pdf_method = pdf_method
        self.replace_pdf = replace_pdf
        self.replace_image = replace_image
        self._cancel_requested = False
        self.errors = []

    def set_merge(self, files: list, output_format: str = "pdf", output_path: str = ""):
        self.operation = "merge"
        self.files = files
        self.merge_output_format = output_format
        self.merge_output_path = output_path
        self._cancel_requested = False
        self.errors = []

    def run(self):
        try:
            if self.operation == "copy":
                self._copy_files()
            elif self.operation == "move":
                self._move_files()
            elif self.operation == "convert":
                self._convert_files()
            elif self.operation == "rename":
                self._rename_files()
            elif self.operation == "compress":
                if self.compression_type == "pdf":
                    self._compress_pdf_files()
                else:
                    self._compress_image_files_with_replace_support()
            elif self.operation == "merge":
                self._merge_files()
        except Exception as e:
            self._record_error(None, str(e))
            self.error.emit(str(e))
