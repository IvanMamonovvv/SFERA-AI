import io

import pytest
from docx import Document

from sfera_ai.services.resume_text_extraction import TextExtractionError, extract_text

_MINIMAL_PDF_WITH_TEXT = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 200 200] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 20 100 Td (Hello resume) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_text_from_valid_pdf_returns_nonempty_text():
    result = extract_text(_MINIMAL_PDF_WITH_TEXT, "application/pdf")

    assert "Hello resume" in result


def test_extract_text_from_valid_docx_returns_nonempty_text():
    file_bytes = _docx_bytes("Опыт работы: 5 лет Python")

    result = extract_text(
        file_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert "Опыт работы: 5 лет Python" in result


def test_extract_text_from_corrupt_pdf_raises_text_extraction_error():
    with pytest.raises(TextExtractionError):
        extract_text(b"not a real pdf", "application/pdf")


def test_extract_text_from_corrupt_docx_raises_text_extraction_error():
    with pytest.raises(TextExtractionError):
        extract_text(b"not a real docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def test_extract_text_unsupported_mime_type_raises_text_extraction_error():
    with pytest.raises(TextExtractionError):
        extract_text(b"whatever", "application/octet-stream")
