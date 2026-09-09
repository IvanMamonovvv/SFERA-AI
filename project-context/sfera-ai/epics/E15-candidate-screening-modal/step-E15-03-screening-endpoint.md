# Шаг E15-03 — `GET .../candidates/screening/`

**Статус:** TODO
**Слой:** Backend (SFERA-AI) · **Зависит от:** E15-01
**Перед началом:** прочитай `docs/superpowers/specs/2026-09-08-candidate-screening-modal-design.md`
(разделы «API», «Данные» — округление); `src/sfera_ai/services/api_read.py`,
`src/sfera_ai/api/routes/candidates.py` (существующий `candidates/` список, E8-02, —
образец контрактных полей).

## Цель

Новый read-эндпоинт: кандидаты курса с `fit_score >= 60`, отсортированные по убыванию,
с флагом `transferred`.

## Что сделать

1. `GET .../candidates/screening/` — фильтр `fit_score >= 60`, сортировка по убыванию
   `fit_score`, поля как в существующем `candidates/` (E8-02) + `transferred: bool`
   (join на `CandidateVacancyTransfer`, E15-01).
2. Отображение — `floor(fit_score / 10)`, не `round` (архитектурное ревью 2026-09-08:
   `round` создаёт визуальное совпадение «6/10» у прошедших и непрошедших порог
   кандидатов из-за рассинхронизации границы округления и порога `>=60`).
3. Пустой список — не ошибка, обычный ответ с пустым массивом.

## Файлы

- `src/sfera_ai/api/routes/candidates.py` — новый роут.
- `src/sfera_ai/services/api_read.py` — функция выборки.

## Критерии готовности (DoD)

- [ ] Фильтр `fit_score >= 60` корректен.
- [ ] Сортировка по убыванию.
- [ ] `transferred: bool` — корректен и для кандидатов без записи в `CandidateVacancyTransfer`.
- [ ] Пустой список курса без прошедших кандидатов → пустой массив, не 404/500.
- [ ] `uv run pytest` — весь сьют зелёный.

## Как проверить

```bash
uv run pytest tests/api/test_candidates_list.py -k screening
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- (не начато)
