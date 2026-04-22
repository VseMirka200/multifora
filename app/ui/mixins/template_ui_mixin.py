# -*- coding: utf-8 -*-

from .template_crud_mixin import TemplateCrudMixin
from .template_params_mixin import TemplateParamsMixin
from .template_apply_mixin import TemplateApplyMixin


class TemplateUiMixin(TemplateCrudMixin, TemplateParamsMixin, TemplateApplyMixin):
    pass
