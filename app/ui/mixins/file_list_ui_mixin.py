# -*- coding: utf-8 -*-

from .file_list_actions_mixin import FileListActionsMixin
from .file_list_context_mixin import FileListContextMixin
from .file_list_preview_mixin import FileListPreviewMixin


class FileListUiMixin(
    FileListActionsMixin,
    FileListContextMixin,
    FileListPreviewMixin,
):
    pass
