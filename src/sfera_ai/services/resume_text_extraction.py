import io

from docx import Document
from pypdf import PdfReader

_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class TextExtractionError(Exception):
    """Файл резюме не парсится — битый файл или неподдерживаемый mime_type."""


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise TextExtractionError(f"не удалось распарсить PDF: {exc}") from exc


def _extract_docx_text(file_bytes: bytes) -> str:
    try:
        document = Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise TextExtractionError(f"не удалось распарсить DOCX: {exc}") from exc


def extract_text(file_bytes: bytes, mime_type: str) -> str:
    """Из байтов файла резюме (PDF/DOCX) достаёт текст. Битый файл или
    неподдерживаемый `mime_type` → `TextExtractionError` (03_TDD.md, «Failure
    Scenarios», «Битый resume») — вызывающий код переводит `ResumeExtract` в `FAILED`."""
    if mime_type == _PDF_MIME:
        return _extract_pdf_text(file_bytes)
    if mime_type == _DOCX_MIME:
        return _extract_docx_text(file_bytes)
    raise TextExtractionError(f"неподдерживаемый mime_type: {mime_type}")
