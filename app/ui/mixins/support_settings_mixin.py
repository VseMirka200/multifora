# -*- coding: utf-8 -*-

from .support_tab_mixin import SupportTabMixin
from .settings_panel_mixin import SettingsPanelMixin
from .detailed_info_mixin import DetailedInfoMixin


class SupportSettingsMixin(SupportTabMixin, SettingsPanelMixin, DetailedInfoMixin):
    pass
