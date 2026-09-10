# Шаг E20-01 — валидация значений criteria_scores (0-10)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E19 (иначе отклонённый ответ → кандидат зависает без
ретрая, см. находку ревью-агента 2026-09-10)
**Перед началом:** прочитай `services/fit_scoring.py::_parse_and_validate` (текущая проверка
`criteria_scores` — только `isinstance(dict)`, без проверки значений), `InvalidFitScoringResponse`
docstring (паттерн — не пишет частичную версию).

## Цель

Ответ LLM с `criteria_scores`-значением вне диапазона 0-10 (шаг 0.5) отклоняется целиком
(`InvalidFitScoringResponse`), не сохраняется как валидный анализ — закрывает баг
"100,0/10" (модель путает шкалу критерия 0-10 со шкалой fit_score 0-100).

## Что сделать

1. В `_parse_and_validate` добавить проверку каждого значения `criteria_scores`: `None`, либо
   число `0 <= x <= 10` с шагом 0.5 (`x * 2 == round(x * 2)`). Строго — не клэмпить/делить на
   10 при значении >10 (softer-фикс маскирует систематическую ошибку модели, см. вывод
   ревью-агента, вопрос A).
2. При нарушении — `raise InvalidFitScoringResponse(...)`, тот же путь, что и другие поля.

## Файлы

- `src/sfera_ai/services/fit_scoring.py` — `_parse_and_validate`.

## Критерии готовности (DoD)

- [ ] `criteria_scores` со значением 100 — `InvalidFitScoringResponse`.
- [ ] `criteria_scores` со значением 10.5 (вне шага 0.5 после округления/вне диапазона) —
      `InvalidFitScoringResponse`.
- [ ] `criteria_scores` со значением 8.5/None — валидно, не ловится.
- [ ] `uv run pytest` — регрессий нет.

## Как проверить

```bash
uv run pytest tests/services/test_fit_scoring.py -k criteria_scores
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-09-10: `_parse_and_validate` (`fit_scoring.py`) — добавлена проверка каждого значения
  `criteria_scores`: `None` пропускается, число вне `[0, 10]` или не кратное 0.5 (шаг проверка
  `value * 2 == round(value * 2)`) → `InvalidFitScoringResponse`. Без клэмпа/деления — строго
  reject, см. вопрос A. 3 новых теста (`-k criteria_scores`), полный `uv run pytest` — 249 passed.
