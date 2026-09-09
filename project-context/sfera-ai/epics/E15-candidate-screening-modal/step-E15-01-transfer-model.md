# Шаг E15-01 — Модель `CandidateVacancyTransfer`

**Статус:** TODO
**Слой:** Backend (SFERA-AI) · **Зависит от:** —
**Перед началом:** прочитай `docs/superpowers/specs/2026-09-08-candidate-screening-modal-design.md`
(разделы «Данные», «Edge cases»).

## Цель

Новая таблица для отметки «кандидат уже передан заказчику» по курсу/вакансии, не
привязанная к версионной истории `CandidateVacancyAnalysis`.

## Что сделать

1. Модель `CandidateVacancyTransfer`: `id`, `candidate_profile_id` (FK →
   `CandidateProfile`), `course_id` (Integer, как в остальных вакансийных джобах),
   `transferred_at` (timestamp).
2. Уникальный индекс на `(candidate_profile_id, course_id)`.
3. Сервисная функция upsert: если запись есть — обновить `transferred_at = now()`;
   если нет — создать. Не «ничего не делать» при повторе (решение владельца
   2026-09-09, зафиксировано в дизайн-документе).
4. Alembic-ревизия.

## Файлы

- `src/sfera_ai/models/candidate_vacancy_transfer.py` — новая модель.
- `migrations/versions/000X_candidate_vacancy_transfer.py` — Alembic-ревизия.
- `src/sfera_ai/services/candidate_transfer.py` (или рядом с export-сервисом) —
  upsert-функция.

## Критерии готовности (DoD)

- [ ] Модель создана, миграция применяется/откатывается на SQLite в тестах.
- [ ] Уникальный индекс подтверждён тестом (повторная вставка не дублирует строку).
- [ ] Upsert обновляет `transferred_at` при повторном вызове — тест на это отдельно.
- [ ] `uv run pytest` — весь сьют зелёный, регрессий нет.

## Как проверить

```bash
uv run alembic upgrade head
uv run pytest tests/models/test_candidate_vacancy_transfer.py
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- (не начато)
