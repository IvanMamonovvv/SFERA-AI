# Шаг E15-06 — Проксирующие endpoint'ы в `sfera_backend`

**Статус:** DONE
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

- `2026-09-09` — реализовано по явному разрешению владельца, вместе с E15-07
  (клиент — зависимость этого шага) в одной сессии. Новый модуль
  `sfera_backend/courses/sfera_ai_proxy_views.py` (не добавлял в уже большой
  `views.py` — план допускал отдельный модуль) — три `APIView`:
  `CandidateScreeningListProxyView` (`GET`), `VacancyProfileProxyCreateView`
  (`POST`), `CandidatesExportProxyView` (`POST`, отдаёт zip как
  `HttpResponse`). Все три — `[IsAuthenticated, CourseCandidatesManagementPermission]`
  (тот же класс, что уже защищает «Выгрузить архив»), курс резолвится через
  существующий `get_demonstration_course_or_404` (импортирован из
  `courses.views`, не продублирован). Вызов SFERA-AI — только через клиент
  E15-07 (`integrations.sfera_ai.client`), не напрямую `requests`. `created_by_id`
  в `vacancy-profile` берётся из `request.user.id`, не из тела запроса (не
  доверяем клиенту). `SferaAiError` → `502` при `status_code=None` (сеть/таймаут),
  иначе статус SFERA-AI пробрасывается как есть (`_sfera_ai_error_response`).
  Маршруты — `v1/courses/<course_uuid>/ai-analysis/{candidates/screening,
  vacancy-profile,export}/` в `api/urls.py`, рядом с `candidate-archive-jobs`
  (не в `courses/urls.py` — такого файла в проекте нет, все маршруты собраны в
  `api/urls.py`, что расходится с текстом плана «courses/urls.py», сверено по
  факту). `drf_spectacular`: добавлен `responses=OpenApiTypes.OBJECT`/`BINARY` на
  все три view — без них `manage.py spectacular` давал 2 новые ошибки
  «unable to guess serializer» (APIView без `serializer_class`), сейчас 0 новых
  (8 ошибок/1 уникальная — все pre-existing, не от этой правки). Тесты — новый
  `courses/tests/test_sfera_ai_proxy_views.py` (13: своя компания admin/HR
  проходит и получает проксированный ответ/zip, чужая компания → 403, кандидат
  → 403, неизвестный курс → 404, `SferaAiError(status_code=None)` → 502,
  `SferaAiError(status_code=404)` → 404 пробрасывается, `requirements`/
  `candidate_profile_ids` отсутствуют в теле → 400) — SFERA-AI вызовы мокаются
  (`courses.sfera_ai_proxy_views.fetch_screening_candidates` и т.д.), реального
  похода к сервису в этих тестах нет (он покрыт `test_client.py`, E15-07).
  `manage.py test courses` — 206/206 зелёных, регрессий нет. Не закоммичено
  (рабочая копия `sfera_backend`) — ждёт решения владельца по коммиту/PR.
