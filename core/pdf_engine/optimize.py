"""Compress PDF image streams without rasterizing pages."""

from io import BytesIO
from pathlib import Path
from shutil import copyfile

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from core.pdf_engine.image_placements import measure_page_images
from core.workers.atomic_output import atomic_output_path


def _shrink(image, sizes, settings):
    reference = image.indirect_reference
    if reference is None or reference.idnum not in sizes:
        return
    stream = reference.get_object()
    color = stream.get("/ColorSpace")
    if color not in ("/DeviceRGB", "/DeviceGray") or stream.get("/BitsPerComponent") != 8:
        return
    filters = stream.get("/Filter", [])
    if isinstance(filters, str):
        filters = [filters]
    if any(name not in ("/DCTDecode", "/FlateDecode", "/ASCII85Decode", "/ASCIIHexDecode") for name in filters):
        return
    if any(key in stream for key in (
        "/Mask", "/SMask", "/Decode", "/ImageMask", "/SMaskInData", "/Alternates", "/F", "/OPI",
    )):
        return
    try:
        if "/DCTDecode" in filters and b"ICC_PROFILE\0" in stream.get_data():
            return
    except (NotImplementedError, OSError, PdfReadError):
        return
    picture = image.image
    if picture is None or picture.mode not in ("L", "RGB") or picture.info.get("icc_profile"):
        return
    width, height = sizes[reference.idnum]
    ppi = settings["gray_resolution" if color == "/DeviceGray" else "color_resolution"]
    target = (max(1, round(width * ppi / 72)), max(1, round(height * ppi / 72)))
    # Skip minor resizes and preserve the original aspect ratio.
    ratio = max(target[0] / picture.width, target[1] / picture.height)
    if 0 < ratio < 2 / 3:
        dimensions = (max(1, round(picture.width * ratio)), max(1, round(picture.height * ratio)))
        picture = picture.resize(dimensions, Image.Resampling.LANCZOS)
    encoded = BytesIO()
    picture.save(encoded, format="JPEG", quality=settings["jpeg_quality"], optimize=True)
    if len(encoded.getbuffer()) >= len(image.data):
        return
    image.replace(picture, quality=settings["jpeg_quality"], optimize=True)


def _optimize_images(writer, settings, should_cancel):
    sizes = {}
    for page in writer.pages:
        if should_cancel():
            raise InterruptedError("Сжатие отменено")
        measure_page_images(page, sizes, should_cancel)
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


def optimize_pdf(source, destination, settings, should_cancel):
    if should_cancel():
        raise InterruptedError("Сжатие отменено")
    source = Path(source)
    reader = PdfReader(source)
    if reader.is_encrypted:
        raise ValueError("Защищённый PDF не поддерживается")
    writer = PdfWriter(clone_from=reader)
    try:
        if settings.get("lossless"):
            for page in writer.pages:
                if should_cancel():
                    raise InterruptedError("Сжатие отменено")
                page.compress_content_streams()
            writer.compress_identical_objects()
        else:
            _optimize_images(writer, settings, should_cancel)
        with atomic_output_path(destination) as temporary:
            with open(temporary, "wb") as stream:
                writer.write(stream)
            if Path(temporary).stat().st_size >= source.stat().st_size:
                copyfile(source, temporary)
            if should_cancel():
                raise InterruptedError("Сжатие отменено")
    finally:
        writer.close()
