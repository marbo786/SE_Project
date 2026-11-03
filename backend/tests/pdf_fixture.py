"""Minimal valid text-PDF fixtures, without adding a PDF-writing runtime dependency."""
def text_pdf(pages):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    font_id = 3 + 2 * len(pages)
    page_ids = []
    for lines in pages:
        page_id, stream_id = len(objects) + 1, len(objects) + 2
        page_ids.append(page_id)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {stream_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode())
        content = b"BT /F1 12 Tf 50 740 Td "
        for index, line in enumerate(lines):
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content += ("0 -16 Td " if index else "").encode() + f"({escaped}) Tj ".encode()
        content += b"ET"
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Count {len(pages)} /Kids [{' '.join(f'{number} 0 R' for number in page_ids)}] >>".encode()
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    output, offsets = bytearray(b"%PDF-1.4\n"), [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output)); output.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)
