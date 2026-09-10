# Шаг E18-01b — job_processing вызывает резюме-пайплайн + чинит facts staleness

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E18-01a (`ensure_resume_processed` в сервисном слое)
**Перед началом:** прочитай `services/job_processing.py`
(`_run_real_ai_call`, `process_batch`, `VACANCY_REASONS`), `services/resume_pipeline.py`
(`ensure_resume_processed` из E18-01a), `services/fit_scoring.py` (`run_fit_scoring`,
что она читает `candidate_profile.facts` как есть), `services/candidate_facts.py`
(`build_or_update_candidate_facts`).

## Проблема

`AIProcessingJob.REASONS` уже включает `NEW_HH_LEAD`/`NEW_APPLICATION`/`NEW_ANSWER`/
`NEW_RESUME`/`NEW_VIDEO` — очередь и раньше "знала" про появление резюме, но
`_run_real_ai_call` эти reason'ы не отличал от прочих: дёргает только `run_fit_scoring`
(вакансийные reason'ы) или `build_or_update_candidate_facts` (остальные) — ни один путь
не скачивает резюме.

## Цель

`_run_real_ai_call` безусловно вызывает `ensure_resume_processed` для любого reason —
резюме кандидата реально скачивается и парсится на каждом тике, где раньше требовался
ручной CLI-запуск. Дополнительно: свежескачанное резюме реально попадает в
`facts`/`fit_score` в рамках того же job (не зависает в `ai_resume_extract`).

## Что сделать

1. **`_run_real_ai_call`** — добавить параметры `hh_client: HHClient`, `s3_client`,
   `s3_bucket: str`. Первая строка функции —
   `ensure_resume_processed(profile, platform_base=platform_base, hh_client=hh_client,
   s3_client=s3_client, s3_bucket=s3_bucket, llm_client=llm_client, session=session)`,
   ДО ветвления по `job.reason in VACANCY_REASONS`. `process_resume()` уже идемпотентен
   и всё нужное для вызова (HH negotiation id или анкетный `Answer`) берётся из уже
   существующего `CandidateProfile` (`hh_negotiation_id`/`application_id`), не из
   джобы — новый reason/новые поля `AIProcessingJob` не нужны. Если `ResumeExtract`
   уже `DONE`, `process_resume` мгновенно возвращает кэш (один `SELECT`), цена вызова
   для уже обработанных кандидатов копеечная.

   Ошибки резюме-пайплайна не пробрасываются наружу (`resume_extraction.py`/
   `resume_fetch.py` перехватывают всё сами и пишут `ResumeExtract.status=FAILED`, не
   бросают исключение) — существующий `try/except` в `process_batch` вокруг
   `_run_real_ai_call` по-прежнему ловит только реальные баги, не ожидаемые
   сетевые/HH-сбои; джоба не уходит в `FAILED`/backoff из-за упавшего резюме.

2. **Ветка `VACANCY_REASONS` (найдено ревью-агентом 2026-09-10, критично):** до
   `run_fit_scoring(...)` добавить вызов `build_or_update_candidate_facts(session,
   platform_base, llm_client, profile)`. Причина: `run_fit_scoring` читает
   `candidate_profile.facts` как есть, не пересобирает из `ResumeExtract` — без
   этого вызова резюме, только что скачанное шагом 1, физически не попадёт в
   `facts`/`fit_score` в рамках этого же job. Более того,
   `compute_current_sources_snapshot` (`change_detection.py`) не следит за
   состоянием `ResumeExtract`, поэтому `needs_profile_rebuild` не станет `True`
   сам по себе — без явного вызова здесь резюме "зависает" в `ai_resume_extract`,
   пока не прилетит несвязанный триггер (новый ответ, новая заявка HH) или явный
   ручной reanalyze. Затрагивает именно целевую популяцию эпика — кандидатов с
   `is_current=True` анализом, заведённых ДО деплоя этого шага
   (`enqueue_fit_recalc_for_course`, `job_detection.py:79-101`).

3. **`process_batch`** — добавить те же три параметра (`hh_client`, `s3_client`,
   `s3_bucket`), прокинуть в `_run_real_ai_call`.

## Файлы

- `src/sfera_ai/services/job_processing.py` — `_run_real_ai_call`/`process_batch`.

## Критерии готовности (DoD)

- [x] `process_batch`/`_run_real_ai_call` принимают `hh_client`/`s3_client`/`s3_bucket`,
  резюме-пайплайн вызывается первой строкой `_run_real_ai_call`, независимо от `job.reason`.
- [x] В ветке `VACANCY_REASONS` `build_or_update_candidate_facts` вызывается ДО
  `run_fit_scoring` (после `ensure_resume_processed`) — свежескачанное резюме реально
  попадает в `facts`/`fit_score` в рамках этого же job, не только в `ai_resume_extract`.
- [x] Новый юнит-тест: `_run_real_ai_call` вызывает `ensure_resume_processed`
  (мок/spy) до ветвления по reason — и для `VACANCY_REASONS`, и для остальных;
  резюме-исключение (если вдруг) не валит джобу без реальной причины.
- [x] Новый юнит-тест: для `VACANCY_REASONS` порядок вызовов —
  `ensure_resume_processed` → `build_or_update_candidate_facts` → `run_fit_scoring`.
- [x] `dry_run=True` (`ai_analysis_dry_run`) по-прежнему не делает ни одного реального
  HH/S3/LLM-вызова — `ensure_resume_processed` вызывается только внутри
  `_run_real_ai_call`, которая и так исполняется лишь при `not dry_run` (не менять
  этот инвариант).
- [x] `uv run pytest` — весь сьют зелёный, регрессий нет.

## Как проверить

```bash
uv run pytest tests/services/test_job_processing.py -v
uv run pytest  # полный сьют, регрессии
```

## Открытые вопросы / риски (для критической оценки перед стартом)

1. **Лишняя нагрузка на каждый тик.** Раньше резюме-пайплайн вызывался только на
   явных прогонах (десятки кандидатов разом). Теперь `ensure_resume_processed`
   дергается на КАЖДОЙ джобе КАЖДОГО тика (до `ai_analysis_max_concurrent_jobs=200`
   джоб/тик) — для уже `DONE`-резюме это 1 лишний `SELECT` на джобу, не критично;
   для кандидатов без резюме вообще (`hh_negotiation_id`/анкета отсутствуют) —
   тоже дёшево (`find_anketa_resume_answer_id` возвращает `None` без похода к HH/S3).
   Реальная стоимость — только для кандидатов, у которых резюме ЕЩЁ не обработано:
   HH-запрос/S3-скачивание/LLM-вызов на каждую такую джобу, пока не станет `DONE`
   или пока не упрётся в лимит попыток (сейчас лимита нет, `FAILED` резюме не
   ретраится автоматически повторно, если джоба сама не упала).
2. **`_run_real_ai_call` перестаёт быть чисто "reason-specific"** — теперь у него
   побочный эффект (резюме) не связанный напрямую с `job.reason`. Осознанный выбор —
   альтернатива (заводить это в `_still_relevant`/отдельный reason) сложнее и
   требует миграции/новых reason, без выигрыша, т.к. `process_resume` и так
   идемпотентен по кандидату, не по джобе.
3. **Ретрай сетевых ошибок HHClient.get_resume_pdf** намеренно не входит в этот шаг —
   без него `_fetch_hh_resume` при разовом сетевом сбое HH API даст `FAILED` без
   повтора, как и раньше. План владельца — реализовать отдельным шагом после E18.

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг — E18-01c).

## Журнал

- `2026-09-10` — шаг выделен из первоначального единого E18-01 (разбивка на 3 шага
  по итогам ревью), с уже внесённым фиксом facts staleness (подтверждён владельцем).
  Реализация не начата — ждёт явного «начинай» от владельца (правило `CLAUDE.md`).
- `2026-09-10` — статус свёрен с кодом. `_run_real_ai_call`/`process_batch`
  (`job_processing.py`) и тесты (`test_job_processing.py`: порядок вызовов для
  profile-reason и `VACANCY_REASONS`, dry_run-инвариант, exception-safety) уже были
  в рабочем дереве, закрывают все пункты DoD — статус-файл просто не обновили. Все
  8 тестов файла зелёные, `uv run pytest` — 234 passed, регрессий нет.
