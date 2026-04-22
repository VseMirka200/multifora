# -*- coding: utf-8 -*-

from .operations_tab_layout_mixin import OperationsTabLayoutMixin
from .operations_compress_ui_mixin import OperationsCompressUiMixin


class OperationsUiMixin(OperationsTabLayoutMixin, OperationsCompressUiMixin):
    pass
