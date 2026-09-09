from io import BytesIO

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from sfera_ai.services.export.pdf_merge import merge_card_with_resume


def _pdf_with_pages(count: int) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    for _ in range(count):
        c.drawString(100, 700, "page")
        c.showPage()
    c.save()
    return buffer.getvalue()


def test_no_resume_returns_card_unchanged():
    card_pdf = _pdf_with_pages(1)

    result = merge_card_with_resume(card_pdf, None, None)

    assert result == card_pdf


def test_pdf_resume_appends_its_pages():
    card_pdf = _pdf_with_pages(1)
    resume_pdf = _pdf_with_pages(2)

    result = merge_card_with_resume(card_pdf, resume_pdf, "pdf")

    assert len(PdfReader(BytesIO(result)).pages) == 3


def test_non_pdf_resume_appends_stub_page_not_raw_bytes():
    card_pdf = _pdf_with_pages(1)

    result = merge_card_with_resume(card_pdf, b"docx-bytes-not-a-pdf", "docx")

    reader = PdfReader(BytesIO(result))
    assert len(reader.pages) == 2
    stub_text = reader.pages[1].extract_text()
    assert "resume.docx" in stub_text
    assert "docx" in stub_text
