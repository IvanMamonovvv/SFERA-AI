# Шаг E11-02 — Пересборка fit-score для погранично прошедших кандидатов с реальным резюме

**Статус:** TODO
**Слой:** Backend/данные · **Зависит от:** E11-01 (HTTP-туннель к backend)
**Перед началом:** прочитай `step-E10-01-full-course-screening.md` (журнал, реальный
прогон 2026-08-31/09-01), эту запись `04_STATE.md`.

## Контекст

Реальный прогон `run_full_course_screening.py --course-id 39` (2026-09-01) дал 6
кандидатов на `fit_score=75` (порог `>75`, ни один формально не прошёл), включая 2
`STRONG_MATCH`. Но `resume-extraction` упал у всех 82 попыток курса (DNS, см. E11-01) —
оценка построена только на анкете, `data_completeness=PARTIAL` у всех шести. Реальное
резюме могло бы существенно изменить fit_score в любую сторону.

`candidate_profile_id` шести пограничных кандидатов (course_id=39):
`2301, 2677, 2760, 3112, 2378, 3026` (application_id: `2271, 1801, 1871, 2076, 2242, 2178`).

## Цель

Для этих 6 кандидатов — реальный resume-extraction (через туннель E11-01) → пересборка
facts → пересчёт fit-scoring. Понять, меняется ли recommendation/fit_score с учётом
резюме, прежде чем решать, пересобирать ли весь 90-прогон курса.

## Что сделать

1. Через туннель E11-01 прогнать `process_resume` для всех 6 `candidate_profile_id` —
   переиспользовать существующий сервисный код (`resume_pipeline.py`), не писать новый.
2. `build_or_update_candidate_facts` на этих же 6 — пересборка facts с учётом резюме.
3. `run_fit_scoring` — новая версия `CandidateVacancyAnalysis`, `is_current` переключится
   автоматически (существующий паттерн версионирования).
4. Сравнить старую (facts из анкеты) и новую (facts из анкеты+резюме) версии —
   fit_score/recommendation/confidence, зафиксировать разницу.
5. Показать сравнение владельцу, вместе решить: пересобирать весь 90-прогон курса 39
   заново или нет (стоимость — реальные LLM-вызовы, решение не в scope этого шага).

## Файлы

Без новых файлов сервисного кода — переиспользование `resume_pipeline.py`,
`candidate_facts.py`, `fit_scoring.py` через одноразовый скрипт/CLI-вызов (решить на
шаге: одноразовый скрипт в `scratchpad` или постоянный CLI-флаг
`run_full_course_screening.py --candidate-ids` — обсудить с владельцем перед реализацией).

## Критерии готовности (DoD)

- [ ] 6 кандидатов имеют новую `CandidateVacancyAnalysis` версию с `data_completeness`
      выше `PARTIAL` (резюме реально учтено) — либо явно зафиксировано, что резюме у
      конкретного кандидата отсутствует на платформе (не баг, а факт)
- [ ] Сравнительная таблица «было/стало» показана владельцу

## Как проверить

```bash
uv run python -c "
from sfera_ai.db.session import make_write_engine
from sqlalchemy import text
engine = make_write_engine()
ids = [2301, 2677, 2760, 3112, 2378, 3026]
with engine.connect() as c:
    for cid in ids:
        row = c.execute(text('SELECT fit_score, recommendation, data_completeness, version FROM ai_candidate_vacancy_analysis WHERE candidate_profile_id=:cid AND is_current=true'), {'cid': cid}).fetchone()
        print(cid, row)
"
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг).

## Журнал

- (пусто)
