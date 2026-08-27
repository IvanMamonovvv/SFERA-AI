# Шаг E4-02 — reflection на `TranscriptionJob`

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E4-01 (гейт пройден — таблица существует)

## Цель

Reflection-набор платформенных таблиц (`platform_db.py`, из E0) расширен
`TranscriptionJob`, читается тестовая запись.

## Что сделать

1. Добавить таблицу `TranscriptionJob` в reflection-набор (по факту названий полей из
   E4-01).
2. Функция `get_transcript_for_answer(answer_id) -> TranscriptionJob | None`,
   фильтр `status='DONE'`.

## Файлы

- `src/sfera_ai/platform_db.py` — расширение reflection-набора
- `src/sfera_ai/services/video_facts.py` — функция чтения
- `tests/services/test_video_facts.py`

## Критерии готовности (DoD)

- [x] Reflection читает `TranscriptionJob` без ошибок на dev-схеме (плюс подтверждено на
  реальном проде через туннель)
- [x] `status != DONE` → `None`, не частичный результат (тест +
  прод-смоук на несуществующий `answer_id`)

## Как проверить

```bash
uv run pytest tests/services/test_video_facts.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — `VIDEO_FACTS_TABLES = ("testchecks_transcriptionjob",)` добавлен в
  `platform_db.py`. `get_transcript_for_answer(platform_base, answer_id)`
  (`src/sfera_ai/services/video_facts.py`) — фильтр `status == "DONE"`, иначе `None`.
  TDD: `tests/services/test_video_facts.py` (3 теста, sqlite in-memory) — RED (ModuleNotFoundError)
  → GREEN. Полный сьют `uv run pytest` — 57 passed, регрессий нет.
  **Прод-смоук** (свой SSH-туннель к staging, туннель закрыт после проверки): первый
  вызов упал `InsufficientPrivilege: permission denied for table testchecks_transcriptionjob`
  — роль `ai_readonly` не имела `GRANT SELECT` на новую платформенную таблицу (тот же класс
  проблемы, что `GRANT REFERENCES`, см. память `project_grant_references_pattern`, только
  для чтения новой таблицы, а не FK). Выполнено `GRANT SELECT ON testchecks_transcriptionjob
  TO ai_readonly;` через `docker exec sfera-staging-db-1 psql -U sfera_app -d sfera_db`
  (владелец дал явное разрешение). После гранта — `get_transcript_for_answer` отработал
  чисто, `None` для несуществующего `answer_id`.
