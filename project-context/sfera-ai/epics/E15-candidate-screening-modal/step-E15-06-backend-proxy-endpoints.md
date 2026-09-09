# Шаг E15-06 — Проксирующие endpoint'ы в `sfera_backend`

**Статус:** TODO
**Слой:** Backend (`sfera_backend`) · **Зависит от:** E15-02, E15-03, E15-04, E15-05
**Репозиторий:** `sfera_backend` — требует отдельного явного разрешения владельца
перед стартом (`CLAUDE.md`), как и весь эпик E14.
**Перед началом:** прочитай `docs/superpowers/specs/2026-09-08-candidate-screening-modal-design.md`
(раздел «Авторизация и межсервисный вызов»); в `FullSphera/sfera_backend/`:
`sfera_backend/core/permissions.py` (`CourseCandidatesManagementPermission`),
`sfera_backend/courses/views.py` (`CandidateArchiveJobCreateView` и соседние —
образец паттерна «create job → poll status»).

## Цель

HR в интерфейсе SPHERA обращается не напрямую к SFERA-AI, а к новым endpoint'ам
FullSphera backend, которые уже проверяют права на курс и затем проксируют вызов в
SFERA-AI.

## Что сделать

1. Три новых view в `courses/views.py` (или отдельном модуле) — по одному на:
   `GET .../candidates/screening/`, `POST .../vacancy-profile/`, `POST .../export/`
   (прокси в соответствующие эндпоинты SFERA-AI, E15-03/E15-04/E15-05).
2. Все три — `permission_classes = [IsAuthenticated, CourseCandidatesManagementPermission]`,
   курс резолвится через `get_demonstration_course_or_404(course_uuid)`.
3. Вызов SFERA-AI — через новый клиент (E15-07), не напрямую `requests`/`httpx` в view.

## Файлы

- `sfera_backend/courses/views.py` (или новый модуль) — новые view.
- `sfera_backend/courses/urls.py` — маршруты.

## Критерии готовности (DoD)

- [ ] Чужая компания/курс → 403/404 (тест, по образцу существующих тестов
      `CandidateArchiveJob*View`).
- [ ] Своя компания, роль admin/user → запрос проходит, проксируется в SFERA-AI.
- [ ] `manage.py test courses` — весь сьют зелёный, регрессий нет.

## Как проверить

```bash
python manage.py test courses -k screening
```

## Как отметить выполнение

1. Журнал в этом файле. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` этого репозитория
   (SFERA-AI) — прогресс по чужому репозиторию трекается здесь, как для E14.

## Журнал

- (не начато — ждёт отдельного разрешения владельца на правку `sfera_backend`)
