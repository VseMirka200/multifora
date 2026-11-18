"""Small self-contained PDFs for integration tests."""

from pathlib import Path

from core.workers.pdfcraft_engine import export_pdf


def create_pdf(path, labels):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    page_ids = [4 + 2 * i for i in range(len(labels))]
    kids = " ".join(f"{number} 0 R" for number in page_ids)
    objects.append(f"<< /Type /Pages /Count {len(labels)} /Kids [{kids}] >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for index, text in enumerate(labels):
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 10 Tf 5 36 Td ({safe}) Tj ET".encode("ascii")
        objects.append(
            (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Resources << /Font << /F1 3 0 R >> >> "
             f"/Contents {page_ids[index] + 1} 0 R >>").encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    Path(path).write_bytes(data)


def read_pdf_text(path, output):
    export_pdf(path, output, "TXT", lambda: False)
    return output.read_text(encoding="utf-8")
