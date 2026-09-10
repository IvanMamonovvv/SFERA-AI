# Шаг E25-02 — прокси-эндпоинт в sfera_backend

**Статус:** DONE
**Слой:** Backend (`sfera_backend`, **другой репозиторий** — требует отдельного явного
разрешения владельца на эту конкретную правку, правило `CLAUDE.md`) · **Зависит от:**
E25-01
**Перед началом:** прочитай `sfera_backend/courses/sfera_ai_proxy_views.py` (три
существующих `APIView` из E15-06 — образец), `sfera_backend/integrations/sfera_ai/client.py`
(E15-07 — образец module-level функции), `CourseCandidatesManagementPermission`.

## Цель

HR-фронтенд (`SPHERA`) может запросить прогресс обработки курса через `sfera_backend`,
не обращаясь к SFERA-AI напрямую — по тому же паттерну, что остальные screening-эндпоинты.

## Что сделать

1. Новая module-level функция `fetch_screening_progress(course_uuid, ...)` в
   `integrations/sfera_ai/client.py` — GET-запрос к `.../vacancy-profile/screening-progress/`
   SFERA-AI, заголовок `X-BFF-Shared-Secret`, по образцу существующих функций клиента.
2. Новый `APIView` в `sfera_ai_proxy_views.py` (или расширение существующего файла) —
   `GET`, защищён `CourseCandidatesManagementPermission` (тот же класс, что уже
   защищает «Выгрузить архив» и остальные три screening-эндпоинта E15-06).
3. Маршрут в `api/urls.py` (не `courses/urls.py`).
4. `drf_spectacular`: `responses=` на новый view, если остальные три задают прецедент.

## Файлы

- `sfera_backend/integrations/sfera_ai/client.py` — новая функция.
- `sfera_backend/courses/sfera_ai_proxy_views.py` — новый view.
- `sfera_backend/api/urls.py` — маршрут.
- `sfera_backend/integrations/sfera_ai/test_client.py`,
  `sfera_backend/courses/test_sfera_ai_proxy_views.py` — тесты.

## Критерии готовности (DoD)

- [ ] Прогресс-эндпоинт отдаёт `{"remaining": int, "failed": int}` (или согласованную на
  E25-01 форму) для курса, к которому у HR есть права.
- [ ] Без прав на курс — 403 (через `CourseCandidatesManagementPermission`, как у соседних
  эндпоинтов — не отдельная проверка).
- [ ] `manage.py test courses integrations.sfera_ai` — без регрессий.
- [ ] `manage.py spectacular` — без новых ошибок схемы.

## Как проверить

```bash
manage.py test courses integrations.sfera_ai
manage.py spectacular --validate
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг — E25-03, требует отдельного «начинай» — другой репозиторий).

## Журнал

- `2026-09-10` — `fetch_screening_progress` в `client.py`, `ScreeningProgressProxyView` в
  `sfera_ai_proxy_views.py`, маршрут `ai-analysis-screening-progress` в `api/urls.py` +
  тесты в обоих test-файлах, по образцу трёх существующих проксей. Docker локально не
  запущен — верификация прогнана на staging-сервере (`ssh sfera`): файлы скопированы в
  запущенный контейнер `sfera-staging-backend-1` (не в образ, временно, только для теста),
  `manage.py test courses integrations.sfera_ai` — 229 тестов OK, `manage.py spectacular
  --validate` — 16 ошибок/77 warnings, все старые (не про новый view), exit 0. Деплой в
  staging-образ не делался — это отдельный шаг, изменения нужно закоммитить/задеплоить
  обычным путём.
