from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate

from sfera_ai.services.export.ai_card import _STYLES

_STUB_TEXT = (
    "Резюме приложено отдельным файлом (resume.{ext}) — "
    "формат .{ext} не поддерживает предпросмотр страницами PDF."
)


def _stub_page_pdf(resume_ext: str) -> bytes:
    """step-E17-03 — не-PDF резюме (docx/картинка/др.) не мерджится страницами,
    вместо этого страница-заглушка в card.pdf с пояснением; сам файл резюме
    остаётся отдельно в ZIP (решение владельца 2026-09-10)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=3 * cm, bottomMargin=3 * cm)
    doc.build([Paragraph(_STUB_TEXT.format(ext=resume_ext), _STYLES["Normal"])])
    return buffer.getvalue()


def merge_card_with_resume(card_pdf: bytes, resume_bytes: bytes | None, resume_ext: str | None) -> bytes:
    """step-E17-03 — резюме следующими страницами того же PDF, что и карточка
    (решение владельца 2026-09-10, заменяет отдельный `resume.<ext>` в ZIP из
    step-E9-03). Резюме не PDF — страница-заглушка вместо страниц резюме, сам
    файл резюме отдельно кладётся в ZIP вызывающим кодом (`archive.py`)."""
    if resume_bytes is None:
        return card_pdf

    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(card_pdf)))
    if resume_ext == "pdf":
        writer.append(PdfReader(BytesIO(resume_bytes)))
    else:
        writer.append(PdfReader(BytesIO(_stub_page_pdf(resume_ext))))

    out = BytesIO()
    writer.write(out)
    return out.getvalue()
