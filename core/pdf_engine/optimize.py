"""Compress PDF image streams without rasterizing pages."""

from io import BytesIO
from math import hypot
from pathlib import Path
from shutil import copyfile

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ContentStream

from core.workers.atomic_output import atomic_output_path

_IDENTITY = (1, 0, 0, 1, 0, 0)


def _compose(local, parent):
    a, b, c, d, e, f = local
    A, B, C, D, E, F = parent
    return (a*A+b*C, a*B+b*D, c*A+d*C, c*B+d*D, e*A+f*C+E, e*B+f*D+F)


def _placements(content, resources, matrix, sizes, active, should_cancel):
    stack = []
    xobjects = resources.get("/XObject")
    if not xobjects:
        return
    xobjects = xobjects.get_object()
    for operands, operator in content.operations:
        if should_cancel():
            raise InterruptedError("Сжатие отменено")
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


def _shrink(image, sizes, settings):
    reference = image.indirect_reference
    if reference is None or reference.idnum not in sizes:
        return
    stream = reference.get_object()
    color = stream.get("/ColorSpace")
    if color not in ("/DeviceRGB", "/DeviceGray") or stream.get("/BitsPerComponent") != 8:
        return
    if any(key in stream for key in ("/Mask", "/SMask", "/Decode", "/ImageMask", "/SMaskInData")):
        return
    picture = image.image
    if picture is None or picture.mode not in ("L", "RGB"):
        return
    width, height = sizes[reference.idnum]
    ppi = settings["gray_resolution" if color == "/DeviceGray" else "color_resolution"]
    target = (max(1, round(width * ppi / 72)), max(1, round(height * ppi / 72)))
    # Keep small changes lossless and preserve the original aspect ratio.
    ratio = max(target[0] / picture.width, target[1] / picture.height)
    if 0 < ratio < 2 / 3:
        dimensions = (max(1, round(picture.width * ratio)), max(1, round(picture.height * ratio)))
        picture = picture.resize(dimensions, Image.Resampling.LANCZOS)
    encoded = BytesIO()
    picture.save(encoded, format="JPEG", quality=settings["jpeg_quality"], optimize=True)
    if len(encoded.getbuffer()) >= len(image.data):
        return
    image.replace(picture, quality=settings["jpeg_quality"], optimize=True)


def optimize_pdf(source, destination, settings, should_cancel):
    if should_cancel():
        raise InterruptedError("Сжатие отменено")
    source = Path(source)
    reader = PdfReader(source)
    if reader.is_encrypted:
        raise ValueError("Защищённый PDF не поддерживается")
    writer = PdfWriter(clone_from=reader)
    try:
        sizes = {}
        for page in writer.pages:
            content = page.get_contents()
            resources = page.get("/Resources")
            if content is not None and resources is not None:
                scale = page.user_unit
                matrix = (scale, 0, 0, scale, 0, 0)
                _placements(content, resources.get_object(), matrix, sizes, set(), should_cancel)
        seen = set()
        for page in writer.pages:
            if should_cancel():
                raise InterruptedError("Сжатие отменено")
            for image in page.images:
                if should_cancel():
                    raise InterruptedError("Сжатие отменено")
                ref = image.indirect_reference
                if ref is not None and ref.idnum not in seen:
                    seen.add(ref.idnum)
                    _shrink(image, sizes, settings)
        with atomic_output_path(destination) as temporary:
            with open(temporary, "wb") as stream:
                writer.write(stream)
            if Path(temporary).stat().st_size >= source.stat().st_size:
                copyfile(source, temporary)
            if should_cancel():
                raise InterruptedError("Сжатие отменено")
    finally:
        writer.close()
