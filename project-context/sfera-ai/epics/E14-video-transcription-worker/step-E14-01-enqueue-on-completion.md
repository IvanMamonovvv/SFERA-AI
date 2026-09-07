# Шаг E14-01 — Постановка в очередь при загрузке видеовизитки

**Статус:** TODO
**Слой:** Backend · **Зависит от:** — (первый шаг эпика)
**Репозиторий:** `sfera_backend` (другой git-репозиторий, НЕ `SFERA-AI`) — требует отдельного
явного разрешения владельца перед стартом (`CLAUDE.md`).
**Перед началом:** прочитай `project-context/PLATFORM_video-transcription-plan/step-02-enqueue-on-completion.md`
(полная спецификация: триггер, идемпотентность, перезапись видео, feature-flag, DoD) и
`EXECUTION_PLAN.md` (место шага в общем порядке).

## Цель

Как только кандидат загрузил видеовизитку — сразу создан `TranscriptionJob(PENDING)`.

## Где делать

`sfera_backend/testchecks/views.py` → `perform_create` (~строки 280–320), где сохраняется
`Answer`. Хук через `transaction.on_commit`, только для `question.question_type ==
VIDEO_RECORDING`. Не трогать `LessonMedia`/`lessons/services/video_processing.py`.

## Файлы

- `sfera_backend/testchecks/views.py` — точка постановки джобы
- `sfera_backend/testchecks/models.py` — `TranscriptionJob.objects.get_or_create`
- env: `TRANSCRIBE_ENABLED` (feature-flag, default off)

## Критерии готовности (DoD)

Полный список — в `step-02-enqueue-on-completion.md`. Кратко:
- [ ] Загрузка видео → ровно один `TranscriptionJob(PENDING)`.
- [ ] Перезапись видео → джоб пере-обрабатывается на финальном файле.
- [ ] `TRANSCRIBE_ENABLED=false` → триггер не срабатывает.

## Как отметить выполнение

1. Журнал в `step-02-enqueue-on-completion.md` (тот файл — источник деталей).
2. Статус здесь → `DONE`, обнови `01_STATE.md` внешнего плана.
3. Обнови `04_STATE.md` этого репозитория (следующий шаг эпика E14).

## Журнал

- (пусто)
