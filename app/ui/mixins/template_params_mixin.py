# -*- coding: utf-8 -*-

from .template_params_base_mixin import TemplateParamsBaseMixin
from .template_params_text_mixin import TemplateParamsTextMixin
from .template_params_numbering_mixin import TemplateParamsNumberingMixin


class TemplateParamsMixin(
    TemplateParamsBaseMixin,
    TemplateParamsTextMixin,
    TemplateParamsNumberingMixin,
):
    pass
