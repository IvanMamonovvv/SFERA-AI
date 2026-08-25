# Шаг E8-04 — `vacancy-profile`/`feedback` CRUD + approve

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E8-01, E1, E7

## Цель

`GET/POST .../vacancy-profile/`, `GET/POST .../feedback/`,
`POST .../feedback/{id}/approve/` работают по контракту TDD.

## Что сделать

1. `vacancy-profile/` GET — текущая `is_current` версия; POST — создаёт новую версию
   (переиспользует versioning-сервис из E1, не пишет вторую реализацию).
2. `feedback/` GET — список по `course`; POST — создаёт `VacancyFeedback`, триггерит
   E7-02 интерпретацию.
3. `feedback/{id}/approve/` — вызывает `approve_feedback` (E7-03) + триггер пересчёта
   (E7-04).
4. Валидация входных данных (Pydantic-схемы), понятные 400 на некорректный ввод.

## Файлы

- `src/sfera_ai/api/routes/vacancy.py`
- `tests/api/test_vacancy_endpoints.py`

## Критерии готовности (DoD)

- [ ] Все три эндпоинта покрыты тестами
- [ ] POST `vacancy-profile/` не переиспользует чужую логику — вызывает существующий
      сервис E1, не дублирует versioning

## Как проверить

```bash
uv run pytest tests/api/test_vacancy_endpoints.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
