"""Measure placements of embedded raster images in PDF points."""

from math import hypot

from pypdf.generic import ContentStream

_IDENTITY = (1, 0, 0, 1, 0, 0)


def _compose(local, parent):
    a, b, c, d, e, f = local
    A, B, C, D, E, F = parent
    return (
        a * A + b * C, a * B + b * D,
        c * A + d * C, c * B + d * D,
        e * A + f * C + E, e * B + f * D + F,
    )


def _placements(content, resources, matrix, sizes, active, should_cancel):
    stack = []
    xobjects = resources.get("/XObject")
    if not xobjects:
        return
    xobjects = xobjects.get_object()
    for operands, operator in content.operations:
        if should_cancel():
            raise InterruptedError("Обработка PDF отменена")
        if operator == b"q":
            stack.append(matrix)
        elif operator == b"Q" and stack:
            matrix = stack.pop()
        elif operator == b"cm":
            matrix = _compose(operands, matrix)
        elif operator == b"Do" and operands[0] in xobjects:
            ref = xobjects.raw_get(operands[0])
            obj = ref.get_object()
            if obj.get("/Subtype") == "/Image" and hasattr(ref, "idnum"):
                width, height = sizes.get(ref.idnum, (0, 0))
                a, b, c, d, _, _ = matrix
                sizes[ref.idnum] = (max(width, hypot(a, b)), max(height, hypot(c, d)))
            elif obj.get("/Subtype") == "/Form" and id(obj) not in active:
                child = ContentStream(obj, content.pdf)
                child_resources = obj.get("/Resources", resources).get_object()
                child_matrix = _compose(obj.get("/Matrix", _IDENTITY), matrix)
                _placements(child, child_resources, child_matrix, sizes, active | {id(obj)}, should_cancel)


def measure_page_images(page, sizes, should_cancel):
    content = page.get_contents()
    resources = page.get("/Resources")
    if content is not None and resources is not None:
        scale = page.user_unit
        matrix = (scale, 0, 0, scale, 0, 0)
        _placements(content, resources.get_object(), matrix, sizes, set(), should_cancel)
