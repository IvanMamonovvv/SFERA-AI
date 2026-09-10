# Шаг E23-02 — `create_vacancy_profile_version` принимает `portrait_text`/`source_url`

**Статус:** DONE
**Слой:** Backend (SFERA-AI) · **Зависит от:** E23-01
**Перед началом:** прочитай `services/vacancy_profile.py::create_vacancy_profile_version`,
`cli/vacancy_profile.py` (оба сабкоманды `create` и `create-from-portrait` — оба вызывают эту
функцию, `create` без портрета вообще).

## Цель

Сервис умеет сохранять `portrait_text`/`source_url` вместе с версией, но НЕ ломает
существующие вызовы без них (CLI `create` — raw JSON без портрета).

## Что сделать

1. `create_vacancy_profile_version(session, *, course_id, requirements, notes, created_by_id,
   portrait_text: str = "", source_url: str | None = None)` — новые параметры ОПЦИОНАЛЬНЫ
   (с дефолтом), не обязательны — иначе ломается CLI `create`-сабкоманда и текущие тесты.
2. Прокинуть оба поля в конструктор `VacancyProfile(...)`.
3. `cli/vacancy_profile.py::cmd_create_from_portrait` — уже вызывает `build_vacancy_requirements`
   и имеет под рукой `portrait_text`/`source_url`, но сейчас НЕ передаёт их дальше в
   `create_vacancy_profile_version` (найдено архитектурным ревью 2026-09-10). Добавить
   `portrait_text=portrait_text, source_url=source_url` в этот вызов — иначе версии,
   созданные через CLI, молча остаются с `portrait_text=""` в отличие от версий через HTTP
   API (E23-03), и это разойдётся незаметно. `cmd_create` (raw JSON, без портрета) — не трогать,
   там этих данных просто нет.

## Файлы

- `src/sfera_ai/services/vacancy_profile.py` — сигнатура + запись полей
- `src/sfera_ai/cli/vacancy_profile.py` — `cmd_create_from_portrait` передаёт
  `portrait_text`/`source_url` в `create_vacancy_profile_version`
- `tests/services/test_vacancy_profile.py` — новые кейсы: с `portrait_text`/`source_url` и без
  (регрессия старого вызова)
- `tests/cli/test_vacancy_profile_cli.py` — проверка, что `create-from-portrait` сохраняет
  `portrait_text`/`source_url` на созданной версии

## Критерии готовности (DoD)

- [x] старые вызовы (`requirements=...` без `portrait_text`) работают как раньше
- [x] новый вызов с `portrait_text`/`source_url` — оба поля сохраняются на `VacancyProfile`
- [x] `uv run pytest tests/services/test_vacancy_profile.py tests/cli/test_vacancy_profile_cli.py` — зелёный

## Как проверить

```bash
uv run pytest tests/services/test_vacancy_profile.py tests/cli/test_vacancy_profile_cli.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-09-10 — `create_vacancy_profile_version` получила опциональные `portrait_text`/`source_url`
  (дефолты `""`/`None`), прокинуты в конструктор `VacancyProfile`. `cmd_create_from_portrait`
  теперь передаёт оба поля дальше. `cmd_create` не тронут. Добавлены тесты: 2 сервисных
  (дефолт/сохранение), 1 CLI (сохранение через `create-from-portrait`, LLM/Settings замоканы).
  Попутно поймал и починил забытый тест `tests/models/test_vacancy_profile.py` — не обновлён
  после E23-01, падал на отсутствии `portrait_text`/`source_url` в списке колонок. Полный
  прогон: 261 passed.
