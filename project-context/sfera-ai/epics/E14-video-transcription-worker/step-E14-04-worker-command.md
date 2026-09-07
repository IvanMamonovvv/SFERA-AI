# Шаг E14-04 — Воркер `run_transcription_worker`

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E14-01, E14-02, E14-03 (нужны модель, провайдер транскрипции и summary)
**Репозиторий:** `sfera_backend` — требует отдельного явного разрешения владельца перед
стартом (`CLAUDE.md`).
**Перед началом:** прочитай `project-context/PLATFORM_video-transcription-plan/step-05-worker-command.md`
(claim_batch с `SKIP LOCKED`, retry, reaper, деплой, DoD).

## Цель

Отдельный процесс дренирует очередь `TranscriptionJob`, безопасно параллелится, переживает пики.

## Где делать

`sfera_backend/testchecks/management/commands/run_transcription_worker.py` (по образцу
`core/.../run_scheduler.py`). `SELECT ... FOR UPDATE SKIP LOCKED` для безопасного pull.

## Файлы

- `sfera_backend/testchecks/management/commands/run_transcription_worker.py` — новый
- env: `TRANSCRIBE_CONCURRENCY=2`, `TRANSCRIBE_MAX_ATTEMPTS=3`

## Критерии готовности (DoD)

Полный список — в `step-05-worker-command.md`. Кратко:
- [ ] Джоб проходит PENDING → PROCESSING → DONE.
- [ ] Два воркера не берут один джоб.
- [ ] Зависший PROCESSING реапится обратно в PENDING.

## Как отметить выполнение

1. Журнал в `step-05-worker-command.md`.
2. Статус здесь → `DONE`, обнови `01_STATE.md` внешнего плана.
3. Обнови `04_STATE.md` этого репозитория.

## Журнал

- (пусто)
