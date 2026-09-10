# Шаг E18-03 — авто-ретрай FAILED резюме (Alembic-миграция)

**Статус:** DONE
**Слой:** Backend + миграция БД · **Зависит от:** E18-01a/b/c (шаг A эпика E18, DONE) —
без него `ensure_resume_processed` не вызывается автоматически, ретраить было бы нечего
**Перед началом:** прочитай `models/resume_extract.py`, `services/resume_pipeline.py`
(`process_resume`, `ensure_resume_processed`), `services/resume_fetch.py` (где `FAILED`
проставляется), `services/resume_extraction.py` (то же для LLM-шага), `models/ai_processing_job.py`
(`attempts`/`retry_after` — образец полей), `services/job_processing.py::backoff`/
`requeue_stuck_jobs`, `scheduler.py::run_requeue_stuck` (образец отдельного cron).

## Проблема

`ResumeExtract.status=FAILED` (сетевой сбой HH/S3, недоступный LLM, битый файл) сейчас
**не ретраится сам по себе**. `process_resume` идемпотентен только в сторону успеха —
если `extract.status == "DONE"`, отдаёт кэш; если `FAILED`, следующий вызов
`ensure_resume_processed` для того же кандидата честно попробует снова, но НОВЫЙ вызов
случится только когда придёт очередная `AIProcessingJob` (новый ответ, новая заявка,
ручной backfill) — событие, не связанное с самим резюме. Кандидат, у которого резюме
один раз не скачалось, может годами не получить ни одного нового триггера и остаться
в `FAILED` навсегда. Найдено при расследовании бага `8e1363e`: 34/82 резюме course_id=39
упали на обрыве соединения — без этого шага их некому пересчитать, кроме ручного CLI.

## Цель

Отдельный периодический cron находит `ResumeExtract.status=FAILED` с истёкшим backoff,
сам вызывает пайплайн заново (`process_resume`) — без участия `AIProcessingJob`/детекции.
Резюме, упавшее на разовом сбое, само доедет до `DONE` в течение нескольких циклов, без
ручного вмешательства. Кандидаты с постоянно битым резюме (файл невалиден, HH навсегда
недоступен) не забрасывают HH/S3/LLM бесконечными попытками — есть потолок `attempts`.

## Что сделать

1. **Alembic-миграция** (`0010_resume_extract_retry.py`, `down_revision="0009"`) —
   добавить в `ai_resume_extract` `attempts INTEGER NOT NULL DEFAULT 0`,
   `retry_after TIMESTAMPTZ NULL`, плюс индекс `(status, retry_after)` — точное зеркало
   `ai_processing_job` (`ix_processing_job_status_retry_after`,
   `models/ai_processing_job.py`). `downgrade()` дропает колонки/индекс обратно.
2. **`ResumeExtract`** (`models/resume_extract.py`) — добавить `attempts: Mapped[int]`
   (`default=0`), `retry_after: Mapped[datetime | None]`.
3. **`services/resume_pipeline.py`** — новая функция `requeue_failed_resumes(session,
   platform_base, *, hh_client, s3_client, s3_bucket, llm_client, max_attempts)`:
   - выбирает `ResumeExtract` с `status="FAILED"`, `attempts < max_attempts`,
     `retry_after IS NULL OR retry_after <= now()`;
   - для каждой строки вызывает `process_resume(...)` с теми же
     `candidate_profile_id`/`source_answer_id`/`hh_resume_id`, что уже записаны в
     самой строке (идентифицирующие поля уже есть — новый lookup по кандидату не
     нужен, `process_resume` найдёт ту же запись по `source_answer_id`/`(candidate_profile_id,
     hh_resume_id)` и продолжит с того места, где раньше упало: если `raw_text` уже
     есть — не перескачивает файл, сразу на LLM-шаг);
   - после вызова: если `extract.status` всё ещё `FAILED` — `attempts += 1`,
     `retry_after = now() + backoff(attempts)` (переиспользовать
     `services/job_processing.py::backoff`, тот же экспоненциальный профиль
     5/10/20/40 минут — не дублировать функцию); если стал `DONE` — `retry_after=None`
     (успех, больше ретраить нечего).
   - строки с `attempts >= max_attempts` в выборку не попадают вообще — остаются
     `FAILED` навсегда, не жгут HH/S3/LLM бюджет бесконечно; отдельного статуса типа
     `DEAD`/`ABANDONED` не заводим (не в скоупе, можно добавить позже отдельным шагом).
4. **`config.py`** — новая настройка `resume_extract_max_attempts: int = 5` (значение
   по умолчанию — предложение, подтвердить с владельцем перед стартом, см. «Открытые
   вопросы» ниже).
5. **`scheduler.py`** — `run_resume_retry(settings)` (по образцу `run_requeue_stuck`),
   регистрация в `build_scheduler` отдельным cron (кандидат: раз в 2 часа — реже
   получасового тика, т.к. каждый вызов — реальный HH/S3/LLM запрос, не дешёвый
   `SELECT`; согласовать точный интервал с владельцем).

## Файлы

- `migrations/versions/0010_resume_extract_retry.py` — новая миграция.
- `src/sfera_ai/models/resume_extract.py` — `attempts`/`retry_after`.
- `src/sfera_ai/services/resume_pipeline.py` — `requeue_failed_resumes`.
- `src/sfera_ai/config.py` — `resume_extract_max_attempts`.
- `src/sfera_ai/scheduler.py` — `run_resume_retry`, регистрация cron.

## Критерии готовности (DoD)

- [ ] Миграция `0010` добавляет `attempts`/`retry_after`/индекс, `upgrade`/`downgrade`
  оба проверены на SQLite (правило владельца — никогда `downgrade` сразу на shared
  staging БД, только `upgrade head` там).
- [ ] `requeue_failed_resumes`: FAILED-строка с истёкшим `retry_after`, LLM теперь
  отвечает успешно → `status=DONE`, `retry_after=None`, `attempts` не увеличивается
  сверх уже накопленного.
- [ ] `requeue_failed_resumes`: FAILED-строка, второй вызов снова падает →
  `attempts += 1`, новый `retry_after = now + backoff(attempts)` (экспоненциальный рост).
- [ ] `requeue_failed_resumes`: строка с `attempts >= max_attempts` НЕ попадает в
  выборку, HH/S3/LLM не вызывается для неё вообще (тест на счётчик вызовов == 0).
- [ ] `requeue_failed_resumes`: `retry_after` в будущем (backoff ещё не истёк) — строка
  пропускается в этом цикле.
- [ ] `run_resume_retry`/`build_scheduler` — cron зарегистрирован, не мешает
  существующим `run_tick`/`run_requeue_stuck`/`run_pii_retention`.
- [ ] `uv run pytest` — весь сьют зелёный, регрессий нет.
- [ ] Read-only инвариант к платформенной БД не нарушен — миграция и новые записи
  только в `ai_*` таблицах.

## Как проверить

```bash
uv run pytest tests/services/test_resume_pipeline.py -v
uv run pytest tests/test_scheduler.py -v
uv run alembic upgrade head   # на SQLite/локально, НЕ на staging без отдельного разрешения
uv run alembic downgrade -1   # проверить откат на SQLite/локально
uv run pytest  # полный сьют, регрессии
```

## Открытые вопросы / риски (для критической оценки перед стартом)

1. **`resume_extract_max_attempts=5` — предложенное значение**, владелец не подтверждал.
   Слишком низкое — постоянно нестабильный HH API забросит резюме раньше времени;
   слишком высокое — бесконечно жжёт бюджет на кандидатов с реально битым файлом.
2. **Интервал cron (предложено раз в 2 часа)** — не подтверждён. Каждый цикл — реальные
   HH/S3/LLM вызовы (в отличие от `run_requeue_stuck`, там только `UPDATE`), нельзя
   ставить так же часто, как получасовой `run_tick`, без риска задвоить нагрузку на
   HH API теми же кандидатами, что уже в очереди через detection.
3. **Пересечение с E18-01b.** Раз в 30 минут `run_tick` и так может доставить новый
   `ensure_resume_processed` для того же кандидата (если появился несвязанный триггер:
   новый ответ, новая заявка) — `requeue_failed_resumes` работает независимо и может
   попытаться параллельно с обычным тиком. `process_resume` идемпотентен на уровне
   БД-записи, но два конкурентных HH/LLM-вызова по одному кандидату — лишний расход,
   не гонка данных. Не критично, но стоит держать в уме при выборе интервала.
4. **34 старых `FAILED`-резюме course_id=39** (упомянуты в `04_STATE.md`) — после
   деплоя этого шага попадут в первый же цикл `requeue_failed_resumes` автоматически
   (если `attempts` у них ещё 0 после миграции) — отдельный ручной пересчёт может не
   понадобиться, но стоит явно решить с владельцем перед деплоем.

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`
(эпик E18 полностью закрыт, если это последний оставшийся шаг).

## Журнал

- `2026-09-10` — шаг расписан по запросу владельца (план не был готов на момент
  завершения шага A эпика E18). Реализация не начата — ждёт явного «начинай» и
  подтверждения открытых вопросов (max_attempts, интервал cron).
- `2026-09-10` — открытые вопросы подтверждены владельцем: `resume_extract_max_attempts=5`,
  интервал cron 2 часа (отдельный от `run_tick`). Реализовано по TDD: модель
  `ResumeExtract` — `attempts`/`retry_after`/индекс `ix_resume_extract_status_retry_after`;
  `services/resume_pipeline.py::requeue_failed_resumes` — выбирает FAILED с истёкшим
  backoff и `attempts < max_attempts`, вызывает `process_resume` по уже сохранённым
  `source_answer_id`/`hh_resume_id` (переиспользует идемпотентность — DONE не трогает
  attempts, повторный FAILED — `attempts+=1`, `retry_after = now + backoff(attempts)`
  через `job_processing.py::backoff`, локальный импорт внутри функции — чтобы не ловить
  циклический импорт с `job_processing.py`, который сам импортирует `ensure_resume_processed`
  из `resume_pipeline.py`). `config.py::resume_extract_max_attempts=5`.
  `scheduler.py::run_resume_retry` — по образцу `run_tick` (HH/S3/LLM клиенты,
  `RESUME_DETECTION_TABLES`), cron `CronTrigger(hour="*/2", minute=0)`, не трогает
  существующий `run_tick`/`run_requeue_stuck`/`run_pii_retention`. Миграция `0010`
  (`down_revision="0009"`) — `upgrade`/`downgrade` оба проверены на отдельной SQLite-БД
  (staged на `0009` через `alembic stamp`, т.к. полный chain с нуля на SQLite падает на
  постгрес-специфичном raw SQL внутри самой 0009 — известное ограничение, не из этого
  шага); staging не даунгрейдился. Тесты: 8 новых (`test_resume_pipeline.py` — success/
  retry-increment/max-attempts-skip/future-retry_after-skip, `test_scheduler.py` —
  клиенты и `max_attempts` прокинуты, `test_resume_extract.py` — обновлён список колонок).
  `uv run pytest` — 242 passed, регрессий нет. Read-only инвариант к платформенной БД не
  нарушен. Эпик E18 полностью закрыт — последний оставшийся шаг.
