"""Compress PDF image streams without rasterizing pages."""

from contextlib import closing
from io import BytesIO
from pathlib import Path
from shutil import copyfile

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import NameObject, NumberObject, StreamObject
from pypdf.generic._image_xobject import _xobj_to_image

from core.pdf_engine.image_placements import measure_page_images
from core.workers.atomic_output import atomic_output_path


def _shrink(writer, object_id, dimensions, settings):
    stream = writer.get_object(object_id)
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
        _, _, picture = _xobj_to_image(stream)
    except (NotImplementedError, OSError, PdfReadError):
        return
    if picture is None:
        return
    with closing(picture):
        if picture.mode != ("L" if color == "/DeviceGray" else "RGB") or picture.info.get("icc_profile"):
            return
        _replace_with_smaller_jpeg(writer, stream, picture, dimensions, settings)


def _replace_with_smaller_jpeg(writer, stream, picture, dimensions, settings):
    width, height = dimensions
    color = stream.get("/ColorSpace")
    ppi = settings["gray_resolution" if color == "/DeviceGray" else "color_resolution"]
    target = (max(1, round(width * ppi / 72)), max(1, round(height * ppi / 72)))
    ratio = max(target[0] / picture.width, target[1] / picture.height)
    resized = picture
    try:
        if 0 < ratio < 2 / 3:
            size = (max(1, round(picture.width * ratio)), max(1, round(picture.height * ratio)))
            resized = picture.resize(size, Image.Resampling.LANCZOS)
        with BytesIO() as encoded:
            resized.save(encoded, format="JPEG", quality=settings["jpeg_quality"], optimize=True)
            jpeg = encoded.getvalue()
        pixel_width, pixel_height = resized.size
    finally:
        if resized is not picture:
            resized.close()
    if len(jpeg) >= len(stream._data):
        return
    # Swap the stream in the writer while preserving its indirect identity and image dictionary.
    properties = {key: value for key, value in stream.items() if key not in {"/Filter", "/DecodeParms", "/Length"}}
    properties.update({
        NameObject("/Filter"): NameObject("/DCTDecode"),
        NameObject("/Width"): NumberObject(pixel_width),
        NameObject("/Height"): NumberObject(pixel_height),
        "__streamdata__": jpeg,
    })
    replacement = StreamObject.initialize_from_dictionary(properties)
    replacement.indirect_reference = stream.indirect_reference
    writer._objects[stream.indirect_reference.idnum - 1] = replacement


def _optimize_images(writer, settings, should_cancel):
    sizes = {}
    for page in writer.pages:
        if should_cancel():
            raise InterruptedError("Сжатие отменено")
        measure_page_images(page, sizes, should_cancel)
    for object_id, dimensions in sizes.items():
        if should_cancel():
            raise InterruptedError("Сжатие отменено")
        _shrink(writer, object_id, dimensions, settings)


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
