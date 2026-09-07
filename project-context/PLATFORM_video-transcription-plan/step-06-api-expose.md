# Step 06 — Отдать транскрипт/summary в API карточки кандидата

**Статус:** ✅ DONE
**Зависит от:** step-01.
**Цель:** в ответе API по кандидату для каждой видеовизитки вернуть статус обработки, транскрипт,
summary (без вердикта — упрощено владельцем 2026-09-07).

## Backend

- Найти сериализатор ответов кандидата (в `testchecks/`/`courses/`, тот, что кормит карточку HR — см. 02_CONTEXT).
- Для ответа-видеовизитки добавить вложенный объект из `answer.transcription_job` (OneToOne):
  ```json
  "transcription": {
    "status": "PENDING|PROCESSING|DONE|FAILED",
    "summary": "…",
    "transcript": "…",       // полный текст, для раскрытия
    "isEmpty": false
  }
  ```
  (без `verdict` — упрощено владельцем 2026-09-07, см. `step-04-summary-provider.md`)
- Если джоба ещё нет (старые отклики до фичи) → `transcription: null` или `status: null`.
- **RBAC:** поле отдаётся только HR/Admin. Кандидату — не отдавать (эндпоинт карточки и так под HR-правами, проверить).
- Обновить OpenAPI: `python manage.py spectacular` + `03_API.md` (правило проекта).

## BFF (Next)

- Поле проходит через существующий BFF-путь карточки кандидата (без нового CORS, правило BFF).
- Проверить, что BFF-прокси прокидывает новое поле as-is.

## Критерий готовности

- [x] GET карточки кандидата возвращает `transcription` для видеоответов.
- [x] Статусы отражают реальное состояние джоба.
- [x] Кандидат/чужая роль поле не получают.
- [x] OpenAPI обновлён (`manage.py spectacular` проходит без ошибок, `TranscriptionJob` в схеме).

## Журнал

- 2026-09-07: реализовано в `sfera_backend` (репозиторий `FullSphera/sfera_backend`,
  явное разрешение владельца на эту правку получено в SFERA-AI сессии).
  - `testchecks/serializers.py`: новый `TranscriptionJobSerializer`
    (`status`/`summary`/`transcript`/`isEmpty`, без `verdict` — упрощено
    владельцем 2026-09-07), поле `transcription` добавлено в
    `CandidateCourseAnswersSerializer` (эндпоинт `GET
    /api/v1/courses/{course_uuid}/candidates/{candidate_id}/answers/`,
    view `CandidateCourseAnswersListView`). `null`, если `TranscriptionJob`
    ещё нет.
  - `testchecks/views.py`: `select_related('transcription_job')` в
    `answers_queryset`, чтобы не плодить N+1 на каждый видео-ответ.
  - RBAC поля отдельно не добавлял — весь эндпоинт уже закрыт
    `CandidateAnswersManagementPermission` (только super-admin/company-admin/
    company-user, кандидат — 403).
  - Тесты: `testchecks/tests/test_candidate_course_answers_transcription.py`
    (transcription при DONE-джобе, `null` без джобы, кандидат — 403).
    Полный прогон `testchecks`+`courses` — 221/221 зелёных.
  - OpenAPI: `manage.py spectacular` без новых ошибок (одна pre-existing
    ошибка в `companies/views.py`, к этой правке не относится).
  - BFF (Next) не трогал — поле проходит как есть через существующий прокси
    (в step написано "без нового CORS" — новых полей маршрутизации не
    требовалось).
  - Отдельного файла `03_API.md` в репозитории не нашёл (в дереве
    `sfera_backend` его нет) — пункт "обновить `03_API.md`" не выполним,
    пропущен.
