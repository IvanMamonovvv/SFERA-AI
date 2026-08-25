# Шаг E9-01 — AI-карточка PDF

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E6, E8
**Перед началом:** прочитай `03_TDD.md» «Future Export».

## Цель

По `candidate_profile_id` рендерится PDF с `CandidateVacancyAnalysis.is_current`
(summary/strengths/risks) + `CandidateProfile.facts`.

## Что сделать

1. Выбрать PDF-рендерер (например `weasyprint`/`reportlab`), зафиксировать выбор.
2. Шаблон карточки — summary/strengths/risks/gaps + ключевые facts.
3. Функция `render_ai_card_pdf(candidate_profile_id, course_id) -> bytes`.

## Файлы

- `src/sfera_ai/services/export/ai_card.py`
- `tests/services/test_ai_card_export.py` — проверка, что PDF генерируется без ошибок
  и не пустой (не сверка визуального вида)

## Критерии готовности (DoD)

- [ ] PDF генерируется на кандидате с полными данными и на кандидате с частичными
      (не падает на отсутствующих полях)

## Как проверить

```bash
uv run pytest tests/services/test_ai_card_export.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано, выбранная библиотека>.
