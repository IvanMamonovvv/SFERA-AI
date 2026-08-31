# Шаг E9-03 — export-эндпоинт/CLI

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E9-01, E9-02, E8 (эндпоинт) — реализуется по
запросу, после появления UI выбора кандидатов (`05_EPICS.md`, эпик E9)

## Цель

Есть способ (API-эндпоинт или CLI) получить архив (AI-карточка + резюме + видеовизитка)
по выбранным кандидатам.

## Что сделать

1. Формат выдачи — согласовать с владельцем на момент реализации (zip-архив на
   несколько кандидатов? По одному файлу за раз?) — **не проектировать заранее без UI**,
   это открытый пункт, зафиксировать решение в журнале при реализации.
2. Эндпоинт/CLI, использующий E9-01+E9-02.

## Файлы

- `src/sfera_ai/api/routes/export.py` — если API
- `src/sfera_ai/cli/export_candidates.py` — если CLI
- `tests/...` — по факту выбранного формата

## Критерии готовности (DoD)

- [ ] Формат согласован с владельцем перед реализацией (этот шаг стартует только когда
      появляется реальный UI-запрос — `05_EPICS.md`)

## Как проверить

```bash
# зависит от выбранного формата, дополнить при реализации
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E9
   → DONE, весь roadmap E0–E9 закрыт).

## Журнал

- `2026-08-31` — выполнено. Формат согласован с владельцем: zip на несколько
  кандидатов, одна подпапка на кандидата (`<folder>/card.pdf`, `/resume.<ext>`,
  `/video.mp4`), недоступный файл → строка в `<folder>/manifest.txt`, не блокирует
  остальные кандидаты/файлы. `full_name` — фолбэк `"Кандидат #<id>"` (платформа не
  хранит ФИО, `first_name`/`last_name` явно обнулены — `PLATFORM_AUDIT_REFERENCE.md`);
  папка кандидата — санитайзинг ФИО или `candidate_<id>` при отсутствии, сейчас всегда
  второе (`candidate_display_name`/`_folder_name`, `src/sfera_ai/services/export/archive.py`).
  Карточка (`ai_card.py`) расширена: `full_name` в заголовке, `criteria_scores`
  таблицей, confidence переведена на русский (`CONFIDENCE_RU`).
  `build_candidates_export_archive(session, platform_base, candidate_profile_ids,
  course_id, *, hh_client, s3_client, s3_bucket) -> bytes` — переиспользует
  `render_ai_card_pdf` (E9-01) и `collect_export_files` (E9-02). Эндпоинт `POST
  .../export/` (`src/sfera_ai/api/routes/export.py`) — тело `{candidate_profile_ids:
  [...]}`, ответ `application/zip`. `create_app()` получил новые фабрики
  `hh_client_factory`/`s3_client_factory` + `app.state.s3_bucket` (`api/app.py`,
  `api/deps.py`) — до этого шага HH/S3-клиенты создавались только в CLI, не в
  веб-слое. Тесты — `tests/services/test_export_archive.py` (3),
  `tests/api/test_export_endpoint.py` (2), расширены `test_ai_card_export.py`.
  Полный сьют `uv run pytest` — 172 passed, регрессий нет. **Эпик E9 (Export)
  полностью завершён**, весь roadmap E0–E9 закрыт.
