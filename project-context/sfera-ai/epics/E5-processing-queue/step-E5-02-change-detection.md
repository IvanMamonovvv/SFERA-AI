# Шаг E5-02 — Change Detection (`needs_profile_rebuild`, `needs_fit_recalc`)

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E5-01
**Перед началом:** прочитай `03_TDD.md` раздел «5. Change Detection — точный алгоритм»
(готовый псевдокод), раздел «7. Риски» → Cost Protection.

## Цель

Обе функции детекции реализованы 1:1 по алгоритму TDD, покрыты тестами на все три
уровня («профиль устарел» / «только вакансия» / «ничего»), не делают ни одного
AI-вызова.

## Что сделать

1. `needs_profile_rebuild(profile) -> bool` — сравнение `sources_snapshot` с текущим
   состоянием источников (Application/Progress/max Answer id/HH negotiation/hh_resume_id).
2. `needs_fit_recalc(profile, course) -> bool` — сравнение `input_snapshot` последнего
   `is_current` анализа с текущей версией `VacancyProfile`/активными `VacancyMemory`.
3. Чистый SQL/ORM-запросы, без побочных эффектов, без сети.

## Файлы

- `src/sfera_ai/services/change_detection.py`
- `tests/services/test_change_detection.py` — три сценария на каждую функцию
  (устарело/не устарело/граница)

## Критерии готовности (DoD)

- [ ] Все три уровня детекции покрыты тестами
- [ ] Ни один тест не мокает AI-вызов (потому что вызовов нет)

## Как проверить

```bash
uv run pytest tests/services/test_change_detection.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
