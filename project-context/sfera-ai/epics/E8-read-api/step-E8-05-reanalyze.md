# Шаг E8-05 — `reanalyze` эндпоинт

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E8-01, E5

## Цель

`POST .../candidates/{id}/reanalyze/` ставит ручную `AIProcessingJob(reason=MANUAL)` для
конкретного кандидата, минуя детекцию.

## Что сделать

1. Эндпоинт создаёт джобу напрямую (без проверки `needs_fit_recalc` — ручной запрос
   всегда ставится, но джоба всё равно идемпотентна на входе в обработку, как и
   остальные — E5-04).
2. Ограничение частоты (rate-limit на ручной реанализ одного кандидата — простая
   защита от случайного спама кнопкой в UI, решить порог и зафиксировать).
3. Ответ — id созданной джобы, статус.

## Файлы

- `src/sfera_ai/api/routes/candidates.py` — расширение
- `tests/api/test_reanalyze.py`

## Критерии готовности (DoD)

- [x] Джоба создаётся с `reason=MANUAL`
- [x] Повторный запрос в пределах rate-limit окна — понятная ошибка, не дубль-джоба

## Как проверить

```bash
uv run pytest tests/api/test_reanalyze.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E8
   → DONE).

## Журнал

- `2026-08-28` — `POST .../candidates/{id}/reanalyze/` (`src/sfera_ai/api/routes/candidates.py`):
  проверка кандидата через `get_candidate_detail` (404 если нет анализа), затем
  `enqueue_manual_reanalyze` (`src/sfera_ai/services/job_detection.py`) ставит
  `AIProcessingJob(reason=MANUAL)`. Rate-limit — 5 минут на кандидата (решение
  владельца), по времени создания последней MANUAL-джобы (не по активным статусам,
  как в `_create_job_if_absent` — ручная джоба обычно уже DONE к повторному клику);
  повтор в окне → `ReanalyzeRateLimitedError` → 429. Тесты — `tests/api/test_reanalyze.py`.
