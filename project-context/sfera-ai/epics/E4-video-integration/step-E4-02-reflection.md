# Шаг E4-02 — reflection на `TranscriptionJob`

**Статус:** TODO
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

- [ ] Reflection читает `TranscriptionJob` без ошибок на dev-схеме
- [ ] `status != DONE` → `None`, не частичный результат

## Как проверить

```bash
uv run pytest tests/services/test_video_facts.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
