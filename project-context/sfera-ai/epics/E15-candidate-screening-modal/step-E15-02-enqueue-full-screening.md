# Шаг E15-02 — `enqueue_full_screening_for_course`

**Статус:** TODO
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

- (не начато)
