# Шаг E14-01 — Постановка в очередь при загрузке видеовизитки

**Статус:** DONE
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

- `2026-09-07` — выполнено. `sfera_backend/testchecks/views.py::QuestionAnswerView.
  perform_create` — после сохранения `Answer` и коммита score/attempt-логики, под
  `settings.TRANSCRIBE_ENABLED` (env, default `False`) и только для
  `question.question_type == VIDEO_RECORDING` с непустым `answer.file`, через
  `transaction.on_commit` ставит `TranscriptionJob.objects.get_or_create(answer=answer)`.
  Кейс «перезапись видео» (сброс джобы в PENDING при новом файле) НЕ реализован —
  проверка кода показала, что `Answer` уникален по `(attempt, question)`, отдельного
  update-эндпоинта нет, повторный `POST` на тот же вопрос падает на `IntegrityError`
  раньше, чем дошёл бы до постановки джобы — ветка сейчас физически недостижима через
  API. Согласовано с владельцем — пропущено, только базовый `get_or_create`.
  Тесты — новый `testchecks/tests/test_transcription_enqueue.py` (3: видео+флаг вкл →
  джоба PENDING; текстовый ответ → джобы нет; флаг выкл → джобы нет); по ходу
  добавлен обязательный `override_settings(STORAGES=..., USE_S3_STORAGE=False)`
  (в этом dev-окружении `USE_S3_STORAGE=True` в реальном `.env` — без форса локального
  диска тест утекал в настоящий S3, конвенция уже используется в
  `lessons/tests/test_lesson_media_api.py` и других). Полный сьют `sfera_backend` —
  632 passed (3 skipped), `ruff check` на изменённых файлах чисто.
  PR отведён от `main` изначально в `develop` — ветки разошлись (`TranscriptionJob`,
  шаг 01, была влита только в `main`, PR #94), из-за чего первый PR тащил лишние
  коммиты/конфликты. Владелец переоткрыл PR в `main` и влил (PR #111). Дополнительно
  сделан обратный проход синхронизации веток: `sync/develop-into-main` (PR #112, main
  получил все 14 коммитов, отставших в develop) и `sync/main-into-develop` (develop
  получил обратно `TranscriptionJob`+эту постановку в очередь + чужой хотфикс HH-лидов
  0-74%, который раньше был только в main) — обе ветки снова синхронны, оба слияния
  без потери функционала (проверено построчным `git diff` в обе стороны).
