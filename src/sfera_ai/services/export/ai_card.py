from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
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
from sfera_ai.services.api_read import (
    resolve_candidate_platform_name,
    resolve_company_name_for_course,
    resolve_vacancy_title_for_course,
)
from sfera_ai.services.candidate_facts import pick_fact_value, resume_status

# step-E12-01 — Helvetica (AFM) не поддерживает кириллицу, весь русский текст в PDF
# рендерился чёрными прямоугольниками. DejaVu Sans — TTF с кириллицей, вендорим файл
# в репозиторий (не pip-зависимость), т.к. на PyPI нет пакета с этим шрифтом.
_FONTS_DIR = Path(__file__).parent / "fonts"
_FONT_REGULAR = "DejaVuSans"
_FONT_BOLD = "DejaVuSans-Bold"
pdfmetrics.registerFont(TTFont(_FONT_REGULAR, str(_FONTS_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(_FONTS_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily(_FONT_REGULAR, normal=_FONT_REGULAR, bold=_FONT_BOLD)

# Шрифт эталона РТХ — Arial-BoldMT/ArialUnicodeMS, не лицензирован для встраивания —
# осознанное ограничение (step-E17-06), форма букв не совпадёт 1-в-1.
_STYLES = getSampleStyleSheet()
_STYLES["Normal"].fontName = _FONT_REGULAR
_STYLES["Title"].fontName = _FONT_BOLD

CONFIDENCE_RU = {"LOW": "низкая", "MEDIUM": "средняя", "HIGH": "высокая"}
RECOMMENDATION_RU = {
    "STRONG_MATCH": "Явно подходит",
    "POSSIBLE_MATCH": "Возможно подходит",
    "WEAK_MATCH": "Слабо подходит",
    "NOT_ENOUGH_DATA": "Недостаточно данных",
    "NOT_A_MATCH": "Не подходит",
}

_DEFAULT_CLIENT_NAME = "SFERA"

# Design tokens эталона РТХ (step-E17-06, hex/pt из pymupdf-экстракции 2026-09-10).
_COLOR_PRIMARY_BLUE = colors.HexColor("#193a63")
_COLOR_WHITE = colors.white
_COLOR_SUBTITLE = colors.HexColor("#087486")
_COLOR_META_BG = colors.HexColor("#f1f6f8")
_COLOR_META_BORDER = colors.HexColor("#c6d5de")
_COLOR_REC_BG = colors.HexColor("#fff7ea")
_COLOR_REC_ACCENT = colors.HexColor("#d18a2d")
_COLOR_BULLET_LEFT = colors.HexColor("#08748a")
_COLOR_BULLET_RIGHT = colors.HexColor("#d18a2d")
_COLOR_BODY_TEXT = colors.HexColor("#354454")
_COLOR_CONTRADICTION = colors.HexColor("#a34b3f")
_COLOR_SCORE = colors.HexColor("#087486")
_COLOR_MUTED = colors.HexColor("#71808d")
_COLOR_RESUME_WARN_BG = colors.HexColor("#fdecea")
_COLOR_RESUME_WARN_ACCENT = colors.HexColor("#c0392b")

RESUME_STATUS_MESSAGE_RU = {
    "MISSING": "Резюме отсутствует",
    "FAILED": "Резюме не удалось обработать",
}

_PAGE_WIDTH = letter[0] - 4 * cm  # margins 2cm слева/справа (SimpleDocTemplate ниже)

_STYLE_NORMAL = _STYLES["Normal"]
_STYLE_NORMAL.fontSize = 7.2
_STYLE_NORMAL.textColor = _COLOR_BODY_TEXT
_STYLE_NORMAL.leading = 9
_STYLE_BULLET = ParagraphStyle("bullet", parent=_STYLE_NORMAL, leftIndent=0.3 * cm)
_STYLE_TITLE = ParagraphStyle(
    "card_title", parent=_STYLES["Title"], fontSize=22.4, leading=26, alignment=0, spaceAfter=2, textColor=_COLOR_PRIMARY_BLUE
)
_STYLE_STRIP = ParagraphStyle("card_strip", parent=_STYLE_NORMAL, textColor=_COLOR_WHITE, fontName=_FONT_BOLD, fontSize=9)
_STYLE_REC_LABEL = ParagraphStyle("rec_label", parent=_STYLE_NORMAL, textColor=_COLOR_REC_ACCENT, fontName=_FONT_BOLD)
_STYLE_SECTION_TITLE = ParagraphStyle(
    "section_title",
    parent=_STYLE_NORMAL,
    textColor=_COLOR_PRIMARY_BLUE,
    fontName=_FONT_BOLD,
    fontSize=10.8,
    leading=13,
    spaceAfter=4,
)
_STYLE_FOOTER = ParagraphStyle("footer", parent=_STYLE_NORMAL, textColor=_COLOR_MUTED, fontSize=6.7, alignment=1)
_STYLE_TOTAL = ParagraphStyle("total", parent=_STYLE_NORMAL, fontSize=7.5)
_STYLE_RESUME_WARN = ParagraphStyle("resume_warn", parent=_STYLE_NORMAL, textColor=_COLOR_RESUME_WARN_ACCENT, fontName=_FONT_BOLD)
_STYLE_SUBTITLE = ParagraphStyle(
    "card_subtitle", parent=_STYLE_NORMAL, textColor=_COLOR_SUBTITLE, fontName=_FONT_BOLD, fontSize=10.6, spaceBefore=2
)
_STYLE_BADGE = ParagraphStyle("card_badge", parent=_STYLE_STRIP, alignment=2)
_STYLE_META = ParagraphStyle("meta", parent=_STYLE_NORMAL, fontName=_FONT_BOLD, fontSize=7.0)
_STYLE_CONTRADICTION = ParagraphStyle("contradiction", parent=_STYLE_NORMAL, textColor=_COLOR_CONTRADICTION, fontName=_FONT_BOLD)


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


def _bullets(items: list[Any] | str | None, style: ParagraphStyle, marker_color: colors.Color) -> list[Paragraph]:
    # `summary` до fit-scoring-v3 (step-E17-05) хранился как строка-абзац, не список —
    # старые записи анализа могут прийти сюда строкой даже после миграции колонки на
    # JSON (миграция не переписывает существующие значения в списки). Без этой
    # нормализации строка распадалась бы на буллеты по одному символу.
    if isinstance(items, str):
        items = [items] if items else []
    marker = f'<font color="{marker_color.hexval()}">■</font>'
    return [Paragraph(f"{marker} {item!s}", style) for item in items] or [Paragraph("—", style)]


def _has_video(facts: list[dict[str, Any]]) -> bool:
    """Видео-статус для плашки — тот же признак, что `has_video` в data_completeness
    (candidate_facts.py) — факт с evidence.source_type == VIDEO."""
    return any((fact.get("evidence") or [{}])[0].get("source_type") == "VIDEO" for fact in facts)


def _fact_value(facts: list[dict[str, Any]], key: str) -> Any | None:
    return pick_fact_value(facts, key)


def _strip_block(strip_label: str, video_present: bool) -> Table:
    badge = "ВИДЕО ЕСТЬ" if video_present else "БЕЗ ВИДЕО"
    table = Table(
        [[Paragraph(strip_label, _STYLE_STRIP), Paragraph(badge, _STYLE_BADGE)]],
        colWidths=[_PAGE_WIDTH * 0.7, _PAGE_WIDTH * 0.3],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _COLOR_PRIMARY_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _header_block(full_name: str, facts: list[dict[str, Any]]) -> list[Any]:
    block: list[Any] = [Paragraph(full_name, _STYLE_TITLE)]
    positions = _fact_value(facts, "positions")
    position = positions[0] if isinstance(positions, list) and positions else None
    if position:
        block.append(Paragraph(str(position), _STYLE_SUBTITLE))
    return block


def _meta_bar(facts: list[dict[str, Any]]) -> Table | None:
    city = _fact_value(facts, "city")
    age = _fact_value(facts, "age")
    experience_years = _fact_value(facts, "experience_years")
    industry = _fact_value(facts, "industry")
    sales_segment = _fact_value(facts, "sales_segment")
    salary = _fact_value(facts, "salary_expectation")

    if city and age:
        cell_city_age = f"{city} · {age} лет"
    elif city:
        cell_city_age = str(city)
    elif age:
        cell_city_age = f"{age} лет"
    else:
        cell_city_age = "—"

    cell_experience = f"{experience_years} лет опыта" if experience_years else "—"

    if industry and sales_segment:
        cell_industry = f"{industry} · {sales_segment}"
    elif industry:
        cell_industry = str(industry)
    elif sales_segment:
        cell_industry = str(sales_segment)
    else:
        cell_industry = "—"

    cells = [
        cell_city_age,
        cell_experience,
        cell_industry,
        f"Ожидание: {salary}" if salary else "—",
    ]
    if all(cell == "—" for cell in cells):
        return None

    table = Table([[Paragraph(cell, _STYLE_META) for cell in cells]], colWidths=[_PAGE_WIDTH / 4] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _COLOR_META_BG),
                ("GRID", (0, 0), (-1, -1), 0.5, _COLOR_META_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _recommendation_block(recommendation: str, interview_questions: list[Any], video_present: bool) -> Table:
    label = "Рекомендация:" if video_present else "Предварительная рекомендация:"
    text = f'<font color="{_COLOR_REC_ACCENT.hexval()}"><b>{label}</b></font> {recommendation}'
    if interview_questions:
        topics = "; ".join(str(item) for item in interview_questions)
        text += f" Уточнить на интервью: {topics}."
    table = Table([[Paragraph(text, _STYLE_NORMAL)]], colWidths=[_PAGE_WIDTH])
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


def _two_col_block(strengths: list[Any], interview_questions: list[Any], video_present: bool) -> Table:
    left_title = "Почему подходит" if video_present else "Сильные стороны"
    right_title = "Что уточнить на интервью"
    col_width = _PAGE_WIDTH / 2 - 0.25 * cm
    left = [Paragraph(left_title, _STYLE_SECTION_TITLE), *_bullets(strengths, _STYLE_BULLET, _COLOR_BULLET_LEFT)]
    right = [
        Paragraph(right_title, _STYLE_SECTION_TITLE),
        *_bullets(interview_questions, _STYLE_BULLET, _COLOR_BULLET_RIGHT),
    ]
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


def _platform_block(summary: list[Any], contradictions: list[Any]) -> Table:
    content: list[Any] = [
        Paragraph("Данные платформы", _STYLE_SECTION_TITLE),
        *_bullets(summary, _STYLE_BULLET, _COLOR_BULLET_LEFT),
    ]
    for contradiction in contradictions:
        content.append(Paragraph(f"Важно: {contradiction}", _STYLE_CONTRADICTION))
    table = Table([[content]], colWidths=[_PAGE_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _COLOR_META_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _resume_status_block(status: str) -> Table | None:
    """Шаг E13-02 — виден только когда резюме не OK, объясняет менеджеру причину
    низкого confidence/fit_score без блокировки скоринга (E13-01)."""
    message = RESUME_STATUS_MESSAGE_RU.get(status)
    if message is None:
        return None
    table = Table([[Paragraph(message, _STYLE_RESUME_WARN)]], colWidths=[_PAGE_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _COLOR_RESUME_WARN_BG),
                ("LINEBEFORE", (0, 0), (0, -1), 6, _COLOR_RESUME_WARN_ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _format_score_value(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}".replace(".", ",")


def _format_criterion_score(score: Any) -> str:
    if score is None:
        return "не оценено"
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "не оценено"
    return f"{_format_score_value(value)}/10"


def _criteria_scores_table(criteria_scores: dict[str, Any]) -> Table:
    rows: list[list[Any]] = [["Критерий", "Балл"]]
    for criterion, score in criteria_scores.items():
        formatted = _format_criterion_score(score)
        rows.append([str(criterion), Paragraph(f'<font color="{_COLOR_SCORE.hexval()}"><b>{formatted}</b></font>', _STYLE_NORMAL)])
    table = Table(rows, colWidths=[_PAGE_WIDTH - 4 * cm, 4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, _COLOR_META_BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), _COLOR_PRIMARY_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), _COLOR_WHITE),
                ("FONTNAME", (0, 0), (-1, -1), _FONT_REGULAR),
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 7.0),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    return table


def render_ai_card_pdf(
    session: Session, candidate_profile_id: int, course_id: int, platform_base: Any = None
) -> bytes | None:
    """step-E9-04 — карточка PDF визуально как в ai-screening-hub (чёрная плашка,
    цветные блоки, таблица баллов), собрана из reportlab Table (без WeasyPrint/HTML —
    журнал step-E9-01, «без cairo/pango в Docker»). Один кандидат — одна страница
    (`KeepTogether`), источник `CandidateVacancyAnalysis.is_current` + `CandidateProfile.facts`.
    None — нет ни одной версии анализа.
    step-E17-06 — визуальный стиль/структура приведены к эталону РТХ; `platform_base`
    опционален (нужен только для брендинга шапки именем заказчика, fallback "SFERA")."""
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

    resume_extracts = session.execute(
        select(ResumeExtract).where(ResumeExtract.candidate_profile_id == candidate_profile_id)
    ).scalars().all()
    resume_status_block = _resume_status_block(resume_status(resume_extracts))

    platform_name = (
        resolve_candidate_platform_name(platform_base, profile)
        if platform_base is not None and profile is not None
        else None
    )
    full_name = candidate_display_name(
        candidate_profile_id, platform_name or _latest_full_name(session, candidate_profile_id)
    )
    confidence_ru = CONFIDENCE_RU.get(current.confidence, "—")
    recommendation_ru = RECOMMENDATION_RU.get(current.recommendation, current.recommendation)
    fit_score_str = _format_score_value(current.fit_score / 10) if current.fit_score is not None else "—"
    video_present = _has_video(facts)
    meta_bar = _meta_bar(facts)
    client_name = (
        resolve_company_name_for_course(platform_base, course_id) if platform_base is not None else None
    ) or _DEFAULT_CLIENT_NAME
    vacancy_title = resolve_vacancy_title_for_course(platform_base, course_id) if platform_base is not None else None
    strip_label = vacancy_title or client_name

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )

    card: list[Any] = [
        _strip_block(strip_label, video_present),
        Spacer(1, 0.3 * cm),
        *_header_block(full_name, facts),
        Spacer(1, 0.3 * cm),
        *([meta_bar, Spacer(1, 0.3 * cm)] if meta_bar is not None else []),
        _recommendation_block(recommendation_ru, current.interview_questions, video_present),
        Spacer(1, 0.4 * cm),
        _two_col_block(current.strengths, current.interview_questions, video_present),
        Spacer(1, 0.4 * cm),
        _platform_block(current.summary, current.contradictions),
        Spacer(1, 0.4 * cm),
        *([resume_status_block, Spacer(1, 0.4 * cm)] if resume_status_block is not None else []),
        Paragraph("Предварительная оценка", _STYLE_SECTION_TITLE),
        (
            _criteria_scores_table(current.criteria_scores)
            if current.criteria_scores
            else Paragraph("Критерии — нет данных", _STYLE_NORMAL)
        ),
        Spacer(1, 0.3 * cm),
        Paragraph(
            f'<font color="{_COLOR_PRIMARY_BLUE.hexval()}"><b>Итог: {fit_score_str}/10 - предварительно, '
            f'{recommendation_ru}.</b></font> '
            f'<font color="{_COLOR_MUTED.hexval()}"><i>Достоверность оценки: {confidence_ru}.</i></font>',
            _STYLE_TOTAL,
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("SFERA | Анализ кандидата по данным резюме и платформы", _STYLE_FOOTER),
    ]
    doc.build([KeepTogether(card)])
    return buffer.getvalue()
