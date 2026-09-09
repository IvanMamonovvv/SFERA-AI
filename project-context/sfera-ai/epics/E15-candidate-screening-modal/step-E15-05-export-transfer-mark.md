# Шаг E15-05 — Экспорт проставляет `CandidateVacancyTransfer`

**Статус:** DONE
**Слой:** Backend (SFERA-AI) · **Зависит от:** E15-01
**Перед началом:** прочитай `docs/superpowers/specs/2026-09-08-candidate-screening-modal-design.md`
(разделы «API», «Edge cases»); `src/sfera_ai/services/export/archive.py`
(`build_candidates_export_archive` — не падает per-candidate, пишет `manifest.txt`),
`src/sfera_ai/api/routes/export.py`.

## Цель

После экспорта помечаются «переданы» только те кандидаты, у кого реально собрался
`card.pdf` — не все id из запроса.

## Что сделать

1. В `POST .../export/` (или в `build_candidates_export_archive`) — собирать список
   id, для которых `render_ai_card_pdf` вернул не `None`.
2. Для этого списка — upsert в `CandidateVacancyTransfer` (E15-01), не для всех
   `candidate_profile_ids` из тела запроса.
3. Кандидаты без карточки — не помечаются «переданы», просто получают `card.pdf:
   недоступно` в `manifest.txt` (текущее поведение не меняется).

## Файлы

- `src/sfera_ai/api/routes/export.py` — обработчик.
- `src/sfera_ai/services/export/archive.py` — возможно, вернуть список успешных id
  наружу вместо `bytes`-only.

## Критерии готовности (DoD)

- [x] Кандидат с успешной карточкой → `CandidateVacancyTransfer` создана/обновлена.
- [x] Кандидат без карточки (нет текущего анализа) → НЕ помечен «передан».
- [x] Смешанный запрос (часть с картой, часть без) → помечены только те, у кого карта.
- [x] `uv run pytest` — весь сьют зелёный.

## Как проверить

```bash
uv run pytest tests/services/test_export_files.py -k transfer
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-09-09 — `build_candidates_export_archive` (`src/sfera_ai/services/export/archive.py`)
  вызывает `mark_candidate_transferred` сразу после успешного `render_ai_card_pdf`, до
  сбора resume/video (transfer не зависит от них). Кандидаты без карточки не трогаются,
  `manifest.txt` — без изменений. Тесты в `tests/services/test_export_archive.py`
  (`test_export_marks_transfer_only_for_candidate_with_card`,
  `test_export_does_not_mark_transfer_for_candidate_without_card`,
  `test_export_mixed_request_marks_only_candidate_with_card`). Весь сьют — 205 passed.
