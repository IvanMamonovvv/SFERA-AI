from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.resume_extract import ResumeExtract

# step-E12-01 — Helvetica (AFM) не поддерживает кириллицу, весь русский текст в PDF
# рендерился чёрными прямоугольниками. DejaVu Sans — TTF с кириллицей, вендорим файл
# в репозиторий (не pip-зависимость), т.к. на PyPI нет пакета с этим шрифтом.
_FONTS_DIR = Path(__file__).parent / "fonts"
_FONT_REGULAR = "DejaVuSans"
_FONT_BOLD = "DejaVuSans-Bold"
pdfmetrics.registerFont(TTFont(_FONT_REGULAR, str(_FONTS_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(_FONTS_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily(_FONT_REGULAR, normal=_FONT_REGULAR, bold=_FONT_BOLD)

_STYLES = getSampleStyleSheet()
_STYLES["Normal"].fontName = _FONT_REGULAR
_STYLES["Title"].fontName = _FONT_BOLD

CONFIDENCE_RU = {"LOW": "низкая", "MEDIUM": "средняя", "HIGH": "высокая"}

_COLOR_BLACK = colors.HexColor("#1a1a1a")
_COLOR_WHITE = colors.white
_COLOR_BLUE = colors.HexColor("#2a5db0")
_COLOR_REC_BG = colors.HexColor("#fff4e5")
_COLOR_REC_ACCENT = colors.HexColor("#e8871e")
_COLOR_REC_LABEL = colors.HexColor("#b35c00")
_COLOR_STRENGTHS = colors.HexColor("#1a7a3c")
_COLOR_GAPS = colors.HexColor("#a6390d")
_COLOR_PLATFORM_BG = colors.HexColor("#eef2f7")
_COLOR_SCORE_HIGH = colors.HexColor("#1a7a3c")
_COLOR_SCORE_MID = colors.HexColor("#b35c00")
_COLOR_SCORE_LOW = colors.HexColor("#a6390d")
_COLOR_FOOTER = colors.HexColor("#999999")
_COLOR_GRID = colors.HexColor("#dddddd")
_COLOR_HEADER_BG = colors.HexColor("#f0f0f0")

_PAGE_WIDTH = A4[0] - 4 * cm  # margins 2cm слева/справа (SimpleDocTemplate ниже)

_STYLE_NORMAL = _STYLES["Normal"]
_STYLE_BULLET = ParagraphStyle("bullet", parent=_STYLE_NORMAL, leftIndent=0.3 * cm)
_STYLE_TITLE = ParagraphStyle("card_title", parent=_STYLES["Title"], alignment=0, spaceAfter=2)
_STYLE_SUBTITLE = ParagraphStyle("card_subtitle", parent=_STYLE_NORMAL, textColor=_COLOR_BLUE, fontName=_FONT_BOLD)
_STYLE_STRIP = ParagraphStyle("card_strip", parent=_STYLE_NORMAL, textColor=_COLOR_WHITE, fontName=_FONT_BOLD, fontSize=9)
_STYLE_REC_LABEL = ParagraphStyle("rec_label", parent=_STYLE_NORMAL, textColor=_COLOR_REC_LABEL, fontName=_FONT_BOLD)
_STYLE_COL_TITLE_STRENGTHS = ParagraphStyle("col_title_strengths", parent=_STYLE_NORMAL, textColor=_COLOR_STRENGTHS, fontName=_FONT_BOLD)
_STYLE_COL_TITLE_GAPS = ParagraphStyle("col_title_gaps", parent=_STYLE_NORMAL, textColor=_COLOR_GAPS, fontName=_FONT_BOLD)
_STYLE_PLATFORM_TITLE = ParagraphStyle("platform_title", parent=_STYLE_NORMAL, fontName=_FONT_BOLD)
_STYLE_FOOTER = ParagraphStyle("footer", parent=_STYLE_NORMAL, textColor=_COLOR_FOOTER, fontSize=8, alignment=1)
_STYLE_TOTAL = ParagraphStyle("total", parent=_STYLE_NORMAL, fontName=_FONT_BOLD)


def candidate_display_name(candidate_profile_id: int, full_name: str | None = None) -> str:
    return full_name if full_name else f"Кандидат #{candidate_profile_id}"


def _latest_full_name(session: Session, candidate_profile_id: int) -> str | None:
    extract = session.execute(
        select(ResumeExtract)
        .where(
            ResumeExtract.candidate_profile_id == candidate_profile_id,
            ResumeExtract.status == "DONE",
        )
        .order_by(ResumeExtract.id.desc())
    ).scalars().first()
    if extract is None:
        return None
    full_name = extract.structured_data.get("full_name")
    return full_name if isinstance(full_name, str) and full_name.strip() else None


def _bullets(items: list[Any], style: ParagraphStyle) -> list[Paragraph]:
    return [Paragraph(f"&bull; {str(item)}", style) for item in items] or [Paragraph("—", style)]


def _strip_block() -> Table:
    table = Table([[Paragraph("КАРТОЧКА КАНДИДАТА · AI-АНАЛИЗ", _STYLE_STRIP)]], colWidths=[_PAGE_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _COLOR_BLACK),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _header_block(full_name: str) -> list[Any]:
    return [
        Paragraph(full_name, _STYLE_TITLE),
        Paragraph("AI-анализ кандидата", _STYLE_SUBTITLE),
    ]


def _recommendation_block(recommendation: str) -> Table:
    text = Paragraph(f'<font color="#b35c00"><b>Рекомендация:</b></font> {recommendation}', _STYLE_NORMAL)
    table = Table([[text]], colWidths=[_PAGE_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _COLOR_REC_BG),
                ("LINEBEFORE", (0, 0), (0, -1), 6, _COLOR_REC_ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _two_col_block(strengths: list[Any], gaps: list[Any]) -> Table:
    col_width = _PAGE_WIDTH / 2 - 0.25 * cm
    left = [Paragraph("Сильные стороны", _STYLE_COL_TITLE_STRENGTHS), *_bullets(strengths, _STYLE_BULLET)]
    right = [Paragraph("Что уточнить", _STYLE_COL_TITLE_GAPS), *_bullets(gaps, _STYLE_BULLET)]
    table = Table([[left, right]], colWidths=[col_width, col_width])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 0.5 * cm),
            ]
        )
    )
    return table


def _fact_line(fact: dict[str, Any]) -> str:
    key = fact.get("key", "")
    value = fact.get("value", "")
    return f"<b>{key}:</b> {value}"


def _platform_block(facts: list[dict[str, Any]]) -> Table:
    content = [
        Paragraph("Данные платформы", _STYLE_PLATFORM_TITLE),
        *_bullets([_fact_line(fact) for fact in facts] if facts else [], _STYLE_BULLET),
    ]
    table = Table([[content]], colWidths=[_PAGE_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _COLOR_PLATFORM_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _score_color(score: Any) -> colors.Color:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return _COLOR_BLACK
    if value >= 8:
        return _COLOR_SCORE_HIGH
    if value >= 5:
        return _COLOR_SCORE_MID
    return _COLOR_SCORE_LOW


def _criteria_scores_table(criteria_scores: dict[str, Any]) -> Table:
    rows: list[list[Any]] = [["Критерий", "Балл"]]
    for criterion, score in criteria_scores.items():
        color = _score_color(score)
        rows.append([str(criterion), Paragraph(f'<font color="{color.hexval()}"><b>{score}</b></font>', _STYLE_NORMAL)])
    table = Table(rows, colWidths=[_PAGE_WIDTH - 4 * cm, 4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, _COLOR_GRID),
                ("BACKGROUND", (0, 0), (-1, 0), _COLOR_HEADER_BG),
                ("FONTNAME", (0, 0), (-1, -1), _FONT_REGULAR),
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    return table


def render_ai_card_pdf(session: Session, candidate_profile_id: int, course_id: int) -> bytes | None:
    """step-E9-04 — карточка PDF визуально как в ai-screening-hub (чёрная плашка,
    цветные блоки, таблица баллов), собрана из reportlab Table (без WeasyPrint/HTML —
    журнал step-E9-01, «без cairo/pango в Docker»). Один кандидат — одна страница
    (`KeepTogether`), источник `CandidateVacancyAnalysis.is_current` + `CandidateProfile.facts`.
    None — нет ни одной версии анализа."""
    current = session.execute(
        select(CandidateVacancyAnalysis).where(
            CandidateVacancyAnalysis.candidate_profile_id == candidate_profile_id,
            CandidateVacancyAnalysis.course_id == course_id,
            CandidateVacancyAnalysis.is_current.is_(True),
        )
    ).scalar_one_or_none()
    if current is None:
        return None

    profile = session.get(CandidateProfile, candidate_profile_id)
    facts = profile.facts if profile is not None else []

    full_name = candidate_display_name(candidate_profile_id, _latest_full_name(session, candidate_profile_id))
    confidence_ru = CONFIDENCE_RU.get(current.confidence, "—")
    fit_score = current.fit_score if current.fit_score is not None else "—"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )

    card: list[Any] = [
        _strip_block(),
        Spacer(1, 0.3 * cm),
        *_header_block(full_name),
        Spacer(1, 0.4 * cm),
        _recommendation_block(current.recommendation),
        Spacer(1, 0.4 * cm),
        _two_col_block(current.strengths, current.gaps),
        Spacer(1, 0.4 * cm),
        _platform_block(facts),
        Spacer(1, 0.4 * cm),
        (
            _criteria_scores_table(current.criteria_scores)
            if current.criteria_scores
            else Paragraph("Критерии — нет данных", _STYLE_NORMAL)
        ),
        Spacer(1, 0.3 * cm),
        Paragraph(f"Fit-score: {fit_score}. Уверенность оценки: {confidence_ru}.", _STYLE_TOTAL),
        Spacer(1, 0.4 * cm),
        Paragraph("SFERA | AI-анализ кандидата по данным резюме и платформы", _STYLE_FOOTER),
    ]
    doc.build([KeepTogether(card)])
    return buffer.getvalue()
