# Шаг E15-02 — `enqueue_full_screening_for_course`

**Статус:** DONE
**Слой:** Backend (SFERA-AI) · **Зависит от:** E15-01
**Перед началом:** прочитай `docs/superpowers/specs/2026-09-08-candidate-screening-modal-design.md`
(разделы «Поток», «Новая сервисная функция», «Известные риски реализации»);
`src/sfera_ai/services/job_detection.py` (`_create_job_if_absent`,
`enqueue_fit_recalc_for_course` — образец), `src/sfera_ai/cli/run_full_course_screening.py`
(образец перебора кандидатов курса).

## Цель

Новая функция ставит `AIProcessingJob` на всех кандидатов курса (включая ещё ни разу
не анализированных), выполняется асинхронно, без гонок при повторном вызове.

## Что сделать

1. `enqueue_full_screening_for_course(session, course_id)` в `job_detection.py`: по
   образцу перебора `Application` из `run_full_course_screening.py` — на каждого
   кандидата `resolve_or_create_candidate_profile` (если профиля нет) + постановка
   джобы через `_create_job_if_absent`.
2. Защита от дублей при конкурентном вызове (двойной клик «Сохранить» — риск найден
   архитектурным ревью 2026-09-08): `_create_job_if_absent` сейчас — только SELECT в
   коде приложения, TOCTOU race возможна. Выбрать один вариант:
   - partial unique index в БД (`ai_processing_job`, `(candidate_profile_id,
     course_id, reason)` `WHERE status IN ('PENDING','PROCESSING')`) + обработка
     `IntegrityError` как no-op; или
   - гвард на вызывающей стороне (не давать второй вызов уйти, пока первый не
     завершился) — решить, где дешевле реализовать на этом шаге.
3. Выполнение — не синхронно в HTTP-запросе (см. E15-04): сама функция должна быть
   вызываемой из фонового обработчика, а не только напрямую из request handler'а.

## Файлы

- `src/sfera_ai/services/job_detection.py` — новая функция.
- `src/sfera_ai/models/ai_processing_job.py` — при выборе варианта с DB-constraint.
- `migrations/versions/000X_...py` — если добавляется индекс.

## Критерии готовности (DoD)

- [ ] Ставит джобы на всех кандидатов курса, включая тех, у кого ещё нет анализа.
- [ ] Дедуп не дублирует уже стоящую `PENDING`/`PROCESSING` джобу того же кандидата.
- [ ] Конкурентный вызов (тест с двумя параллельными вызовами в разных транзакциях/потоках)
      не создаёт дублирующую джобу.
- [ ] `uv run pytest` — весь сьют зелёный.

## Как проверить

```bash
uv run pytest tests/services/test_job_detection.py -k full_screening
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-09-09: реализовано.
  - `enqueue_full_screening_for_course(session, platform_base, course_id)` в
    `job_detection.py` — перебор всех `Application` курса (по образцу
    `run_full_course_screening.py`), `resolve_or_create_candidate_profile` +
    `_create_job_if_absent(reason="BACKFILL")`.
  - Защита от гонки — выбран вариант с DB-constraint (не guard на вызывающей стороне,
    т.к. вызывающая сторона — другой репозиторий, `FullSphera`, правки требуют
    отдельного разрешения). Partial unique index `(candidate_profile_id, course_id,
    reason) WHERE status IN ('PENDING','PROCESSING')` уже стоял в БД с миграции 0004,
    но отсутствовал в объявлении модели `AIProcessingJob.__table_args__` — из-за этого
    `Base.metadata.create_all` (тестовая SQLite-схема) constraint не создавал. Добавлен
    в модель тем же `Index(..., unique=True, postgresql_where=..., sqlite_where=...)`.
  - `_create_job_if_absent` теперь ловит `IntegrityError` на `commit()` как no-op
    (rollback + `return None`) — закрывает TOCTOU-гонку между SELECT и INSERT.
  - Тесты (`tests/services/test_job_detection.py`): `test_full_screening_enqueues_for_all_course_applications`,
    `test_full_screening_does_not_duplicate_pending_job`,
    `test_concurrent_create_job_if_absent_no_duplicate` (два потока, разные `Session`
    на файловой SQLite, барьер между SELECT и INSERT — воспроизводит реальную гонку).
  - `uv run pytest tests/` — 197 passed.

Не сделано в рамках этого шага (не входит в объём — другой репозиторий): вызов из
фонового обработчика/`POST vacancy-profile/` в `sfera_backend`/`FullSphera` — см.
step-E15-04.
