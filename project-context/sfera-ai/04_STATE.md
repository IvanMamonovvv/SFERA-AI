# STATE — где мы остановились

> **Единственный источник правды о прогрессе.** Обновляй после каждого шага.
> Новый чат: читай сверху вниз, бери первый шаг со статусом `TODO`.

**Проект/фича:** SFERA-AI — AI-анализ кандидатов, единственный инструмент этого репозитория
**Последнее обновление:** `2026-08-28` — эпик **E6 (Fit scoring) полностью завершён**.
`step-E6-04`/`step-E6-05` закрыты реальными прод-прогонами на `course_id=25` («Менеджер
по продажам (ШКМ)»): создан CLI `run_fit_scoring_sample.py`, черновой `VacancyProfile`
id=3, сборка фактов + fit-scoring на 20 реальных кандидатов (≈$0.0004/кандидат по
ориентировочному тарифу gpt-4o-mini). Владелец подтвердил и черновик требований, и
вердикты модели. Побочно найдено и закрыто: `ai_readonly` не имел `GRANT SELECT` на
`courses_course`/`courses_progress`/`testchecks_testattempt` — гранты выданы (владелец
подтвердил каждый). Флаг `ai_processing_dry_run` для непрерывной автообработки через
очередь сознательно НЕ снят — планировщик (`scheduler.py`) физически не задеплоен на
проде как постоянный процесс (`Dockerfile` CMD — временный `smoke_test`, реальный
entrypoint — предмет **E8**); включать его раньше деплоя бессмысленно и рискованно.
Детали — журналы `step-E6-04-queue-integration.md`/`step-E6-05-manual-validation.md`.
Следующий шаг — эпик **E7** (Vacancy Feedback/Memory).

`2026-08-27` — реальный прогон всего эпика E5 на staging
(владелец попросил проверить, хватит ли текущих лимитов очереди на 100-200 кандидатов/сутки
по 3 вакансиям ~400 каждая). Три находки:
1. **Реальный баг** в уже `DONE` шаге `step-E5-02-change-detection.md`:
   `needs_profile_rebuild` читал несуществующую колонку `updated_at` вместо реальной
   `modified_at` (Django-модели платформы) — юнит-тесты не ловили, т.к. самодельная
   SQLite-схема в фикстурах повторяла ту же ошибку, а не реальную схему. Исправлено в
   `change_detection.py` + тестовых фикстурах (`test_change_detection.py`,
   `test_job_detection.py`). Детали — журнал `step-E5-02-change-detection.md`.
2. **Пропускная способность не считалась под реальный объём.** Старый конфиг
   (`ai_analysis_max_concurrent_jobs=5` × 3 тика/сутки `8,15,19` = 15 джоб/сутки) не
   успевал бы за притоком 100-200 кандидатов/сутки — очередь росла бы бесконечно.
   Пересчитано: `ai_analysis_max_concurrent_jobs=200`, тик каждые 30 минут
   (`CronTrigger(minute="*/30")` вместо фиксированных часов) — запас на порядок.
   Стоимость реального AI-вызова (E6-04, deньги за LLM) ещё не считалась — промпт
   fit-scoring не спроектирован; в `step-E6-04-queue-integration.md` добавлен явный
   пункт «прикинуть токены/цену до снятия dry-run».
3. Детекция на реальном staging создала 403 `PENDING`-джобы разом (весь бэклог
   кандидатов без профиля, не только «новые за день») — подтверждает, что первый
   реальный прогон после долгого простоя даёт вспышку, а не равномерный поток.
`uv run pytest` — 82 passed после всех правок, регрессий нет. Шаг `step-E5-06-hh-lead-pii-ttl.md`
(само задание) выполнен отдельно: `purge_expired_hh_lead_resumes(session, ttl_days)` в
`services/pii_retention.py` — UPDATE (не DELETE) `raw_text`/`structured_data` у
`ResumeExtract` для `hh_negotiation`-only профилей (`application_id IS NULL`) старше
`RESUME_PII_TTL_DAYS` (default 90). Отдельный суточный cron `run_pii_retention` в
`build_scheduler()` (03:00). Эпик E5 всё ещё не завершён — остался
`step-E5-07-merge-detection.md`.

## Внешние гейты / блокеры

**E4 разблокирован** (`2026-08-27`): владелец реализовал и раскатал модель `TranscriptionJob`
в `sfera_backend` (шаг 01 внешнего плана `PLATFORM_video-transcription-plan/`, влито в `main`
PR #94, применено на проде). E4-02 (reflection + `get_transcript_for_answer`) выполнен и
подтверждён на реальной БД. Остальные шаги внешнего пайплайна (очередь, whisper-провайдер,
LLM summary, воркер) пока не реализованы — не блокируют E4-02/03 (нужна только сама таблица),
но реальных `DONE`-записей в проде ещё не появится, пока внешний пайплайн не заработает целиком.

Кроме этого блокеров нет. Роль `ai_readonly` создана на прод-Postgres 2026-08-26 (владелец дал явное
разрешение), см. журнал `step-E0-04-ssh-tunnel.md` и `step-E0-05-smoke-test.md`.

6 открытых вопросов (`02_CONTEXT.md`) — ни один не блокирует старт разработки,
решаются по ходу, на своих шагах реализации.

## Текущий следующий шаг

Эпики E0–E6 завершены. Следующий — эпик **E7** (Vacancy Feedback/Memory workflow,
зависит только от E1) по графу зависимостей `05_EPICS.md`. E8 (Read API) не начинать
раньше E7 — явная зависимость.

**Не начинать без явного «начинай»/«приступай» от владельца** — план и код разделены
явным согласованием (правило проекта).

## Доска статусов

| Эпик/# | Шаг | Статус | Завершён |
|---|---|---|---|
| — | Архитектура (единый `ARCHITECTURE.md`, до реструктуризации) | DONE | 2026-08-21 |
| — | Решение об отдельном сервисе/репозитории | DONE | 2026-08-25 |
| — | Реструктуризация плана в PRD/CONTEXT/TDD/EPICS/STATE | DONE | 2026-08-25 |
| E0-01 | Bootstrap сервиса + reflection smoke-test (scaffold, env-config, reflection, tunnel, smoke-test код, Dockerfile, shared docker-сеть, роль `ai_readonly` создана, прогон на проде подтверждён) | DONE | 2026-08-26 |
| E1-01 | `VacancyProfile` модель + CRUD | DONE | 2026-08-26 |
| E2-01 | `CandidateProfile` identity resolver | DONE | 2026-08-26 |
| E3-01 | `ResumeExtract` пайплайн (модель, получение файла, извлечение текста, LLM structured extraction, оркестрация+кэш) | DONE | 2026-08-27 |
| E4-01 | Проверка готовности `TranscriptionJob` (гейт) | DONE | 2026-08-27 |
| E4-02 | Reflection на `TranscriptionJob` | DONE | 2026-08-27 |
| E4-03 | Адаптер видео-фактов для сборки профиля | DONE | 2026-08-27 |
| E5-01 | `AIProcessingJob` + очередь (dry-run, включая E5-07 merge detection) | DONE | 2026-08-27 |
| E6-01 | Fit scoring — сборка `CandidateProfile.facts` (`step-E6-01-profile-assembly.md`) | DONE | 2026-08-27 |
| E6-02 | `CandidateVacancyAnalysis` модель + Alembic (`step-E6-02-analysis-model.md`) | DONE | 2026-08-27 |
| E6-03 | Реальный LLM Fit-вызов, версии, `is_current` (`step-E6-03-llm-fit-call.md`) | DONE | 2026-08-27 |
| E6-04 | Включение реальных AI-вызовов в очередь (`step-E6-04-queue-integration.md`) | DONE | 2026-08-28 |
| E6-05 | Ручной прогон и сверка с HR (`step-E6-05-manual-validation.md`) | DONE | 2026-08-28 |
| E7-01 | Vacancy Feedback/Memory workflow | TODO | — |
| E8-01 | Read API | TODO | — |
| E9-01 | Export | TODO | — |

## Журнал (дополнять, не стирать)

- `2026-08-28` — эпик **E6 (Fit scoring) завершён**: `step-E6-04-queue-integration.md`
  и `step-E6-05-manual-validation.md` закрыты. Реальный прод-прогон на `course_id=25`
  («Менеджер по продажам (ШКМ)», найден по UUID `fb16645fbe35418ea3342734becc489b` через
  `courses_course.course_uuid` — понадобился отдельный `GRANT SELECT` на `courses_course`/
  `courses_progress`/`testchecks_testattempt` для `ai_readonly`, владелец подтвердил).
  Новый CLI `src/sfera_ai/cli/run_fit_scoring_sample.py` (ручной прогон, round-robin
  выборка по `data_completeness`, CSV/stdout вывод) — то, что требовал `step-E6-05`.
  Создан черновой `VacancyProfile` id=3 v1 для course 25 (владелец подтвердил «пока
  устраивает», не финальный текст). 20 реальных кандидатов прогнаны через полный
  пайплайн (`build_or_update_candidate_facts` + `run_fit_scoring`): 12× `NOT_ENOUGH_DATA`
  (у всех — только 3 факта, contact-info, анкета не дозаполнена самим кандидатом — не
  баг), 5× `POSSIBLE_MATCH`, 1× `WEAK_MATCH`, 1× `NOT_A_MATCH` — у кандидатов с 8+
  фактами. Владелец сверил и подтвердил «адекватно» — правка промпта не потребовалась.
  Стоимость по факту (п.0 E6-04) — ≈$0.0004/кандидат (facts+fit, ориентировочный тариф
  gpt-4o-mini через OpenRouter, точную ставку сверить в дашборде OpenRouter). Флаг
  `ai_processing_dry_run` для автоматической обработки через очередь сознательно НЕ
  снят — планировщик (`scheduler.py`) физически не задеплоен на проде как постоянный
  процесс (`Dockerfile` CMD — временный `smoke_test`, реальный entrypoint — E8);
  решение владельца — включать раньше деплоя бессмысленно, вернуться к этому на E8 с
  отдельным подтверждением. Полный сьют `uv run pytest` — 110 passed, регрессий нет
  (код в этой сессии не менялся, кроме нового CLI). Следующий шаг — эпик **E7** (Vacancy
  Feedback/Memory workflow).
- `2026-08-27` — шаг `step-E6-04-queue-integration.md` — код диспетчера выполнен,
  **шаг не DONE** (первый реальный платный AI-вызов на проде ещё не запускался,
  нужно отдельное подтверждение владельца после оценки стоимости — п.0/п.2 DoD шага).
  `process_batch` (`job_processing.py`) диспетчерит по `reason`:
  `VACANCY_PROFILE_CHANGED`/`FEEDBACK_APPLIED` → `run_fit_scoring` (E6-03), остальные
  → `build_or_update_candidate_facts` (E6-01). Идемпотентность: реальный AI-вызов —
  только когда `_still_relevant` ещё true и `dry_run=False`, иначе `DONE` без вызова.
  Новый `pilot_course_id` (`config.py` → `ai_processing_pilot_course_id`) ограничивает
  реальные вызовы одним `course` при снятом dry-run; вне пилота джоба остаётся `PENDING`.
  Профильные джобы резолвят `course` через `CandidateProfile.application_id` →
  `courses_application.course_id` (нет прямой связи в модели). `scheduler.py` собирает
  `OpenRouterClient` и передаёт в `process_batch`. Тесты — 4 новых
  (`tests/services/test_job_processing.py`, моки диспетчеризации/пилота, без реальных
  LLM/платформенных вызовов). Полный сьют `uv run pytest` — 110 passed, регрессий нет.
  Детали и что осталось перед прод-пилотом — журнал step-файла.
- `2026-08-27` — шаг `step-E6-03-llm-fit-call.md` выполнен: `run_fit_scoring()`
  (`src/sfera_ai/services/fit_scoring.py`) — промпт из `CandidateProfile.facts` +
  `VacancyProfile.requirements` + `memory_rule_texts` (пустой список — `VacancyMemory`
  ещё не реализована, E7), вызов `OpenRouterClient.complete` (E3-04), строгая валидация
  JSON-ответа (choices `confidence`/`recommendation`, диапазоны `fit_score`/
  `data_completeness`, типы списков/dict) — при любом нарушении бросает
  `InvalidFitScoringResponse` ДО записи в БД (LLM-вызов и валидация целиком до
  session.add/commit). `LLMProviderError` не перехватывается, пробрасывается наверх
  (обработка на уровне очереди — E5). Транзакция версии — по паттерну
  `services/vacancy_profile.py`: снять `is_current` со старой версии + `flush()` до
  insert новой, один `commit()`. `input_snapshot` = `sources_snapshot` +
  `vacancy_profile_id` + `memory_ids`. `cost_estimate` оставлен `None` — нет
  согласованной тарифной формулы, поле готово на будущее. Тесты —
  `tests/services/test_fit_scoring.py` (6). Полный сьют `uv run pytest` — 107 passed,
  регрессий нет. Эпик E6 не завершён — дальше `step-E6-04-queue-integration.md`.
- `2026-08-27` — шаг `step-E5-07-merge-detection.md` выполнен, эпик E5 завершён:
  модель `AiServiceState` (key-value курсор, `src/sfera_ai/models/ai_service_state.py`),
  ревизия `0006`, `detect_and_process_merges` в `src/sfera_ai/services/merge_detection.py`
  — переносит `application_id` или проставляет `is_superseded`/`superseded_by_id` по
  `CandidateMergeLog` (03_TDD.md, «Candidate Identity — Merge кандидатов»). Реальные
  колонки `courses_candidatemergelog` проверены живой reflection'ом на staging перед
  реализацией (`canonical_application_id`/`duplicate_application_id`, не `source`/
  `target` — TDD предупреждал не копировать псевдокод как есть, разошёлся только
  комментарий, не структура). Побочно найден и исправлен пробел: `detect_and_enqueue`
  (`job_detection.py`) не фильтровал `is_superseded=False` в выборке для
  `CANDIDATE_DATA_CHANGED` — добавлен фильтр. Тесты — `tests/models/test_ai_service_state.py`
  (2), `tests/services/test_merge_detection.py` (5). Upgrade head применён на staging
  через туннель (FK на платформу нет, GRANT не нужен); upgrade+downgrade полного цикла
  проверен на отдельной SQLite. Полный сьют `uv run pytest` — 101 passed, регрессий нет.
- `2026-08-27` — шаг `step-E6-02-analysis-model.md` выполнен: модель
  `CandidateVacancyAnalysis` (`src/sfera_ai/models/candidate_vacancy_analysis.py`),
  ревизия `0005` (`migrations/versions/0005_ai_candidate_vacancy_analysis.py`), тесты
  `tests/models/test_candidate_vacancy_analysis.py` (6). `vacancy_profile_id` —
  `ForeignKey(..., ondelete="RESTRICT")` (PROTECT, в отличие от остальных FK этой модели),
  подтверждено тестом с `PRAGMA foreign_keys=ON` на SQLite. `course_id` без
  SQLAlchemy `ForeignKey` в модели (платформенная таблица, как у `AIProcessingJob`) — FK
  на `courses_course` только в raw-миграции. Upgrade head применён на staging через
  туннель (GRANT REFERENCES на `courses_course` уже был выдан в E1-09, новых не
  потребовалось); upgrade+downgrade полного цикла проверен на отдельной SQLite-БД.
  Полный сьют `uv run pytest` — 94 passed, регрессий нет.
- `2026-08-27` — шаг `step-E6-01-profile-assembly.md` выполнен:
  `build_or_update_candidate_facts()` (`src/sfera_ai/services/candidate_facts.py`) —
  инкрементальная сборка `CandidateProfile.facts` из ответов (батч-LLM), готовых
  `ResumeExtract` (без LLM), готовых видео-транскриптов (без LLM). Триггер — вынесенный
  из `change_detection.needs_profile_rebuild` в переиспользуемую
  `compute_current_sources_snapshot`. Вне scope: создание `ResumeExtract` для
  `ANKETA_FILE`-ответа (детекция+`process_resume`) — только чтение уже `DONE`; это
  переносится в `E6-04`/отдельный шаг. `data_completeness` пороги (0→MINIMAL,
  1-2→PARTIAL, 3-4→FULL) — решение принято на этом шаге, TDD точных порогов не
  фиксировал. Полный сьют — 88 passed.
- `2026-08-27` — шаг `step-E5-06-hh-lead-pii-ttl.md` выполнен:
  `purge_expired_hh_lead_resumes(session, ttl_days)` в `src/sfera_ai/services/pii_retention.py`
  — `SELECT ... JOIN CandidateProfile WHERE application_id IS NULL AND processed_at <
  now()-ttl_days`, затем `raw_text=""`/`structured_data={}` в Python (SQLite в тестах
  не поддерживает bulk-UPDATE-эквивалент из шаблона шага один-в-один, семантика та же —
  `status`/строка не трогаются). Новая настройка `resume_pii_ttl_days` (default `90`,
  заглушка — точное число согласовать с владельцем перед прод). Отдельный суточный cron
  `run_pii_retention` в `build_scheduler()` (`CronTrigger(hour=3, minute=0)`, вне
  пиковых 8/15/19 тиков). Тесты `tests/services/test_pii_retention.py` — 3 (просроченный
  hh-lead-only очищен, конвертировавшийся `application_id` не трогается даже если старый,
  свежий hh-lead-only не трогается). Полный сьют `uv run pytest` — 82 passed, регрессий
  нет. Эпик E5 не завершён — дальше `step-E5-07-merge-detection.md`.
- `2026-08-27` — шаг `step-E5-05-stuck-jobs.md` выполнен: `requeue_stuck_jobs(session,
  threshold_hours)` в `job_processing.py` — `UPDATE ... WHERE status=PROCESSING AND
  started_at < now()-threshold` → `PENDING`, `attempts += 1`, `started_at = None` (не
  `FAILED` — не вина джобы). Зарегистрирован отдельным часовым job'ом в
  `build_scheduler()` (`run_requeue_stuck`, `CronTrigger(minute=0)`, отдельно от
  3-разового тика). Новая настройка `ai_stuck_job_threshold_hours` (default `2`).
  Тесты — +2 (зависшая → requeue, свежая не трогается). Полный сьют `uv run pytest` —
  79 passed, регрессий нет. Инструкция шага «эпик E5 → DONE» неточна — в каталоге ещё
  есть `step-E5-06-hh-lead-pii-ttl.md`/`step-E5-07-merge-detection.md` (TODO), эпик E5
  не завершён. Дальше — `step-E5-06-hh-lead-pii-ttl.md`.
- `2026-08-27` — шаг `step-E5-04-scheduler-dry-run.md` выполнен: `process_batch`
  (`src/sfera_ai/services/job_processing.py`) — `SELECT ... FOR UPDATE SKIP LOCKED` на
  `PENDING`-джобы, per-джоба try/except (упавшая не блокирует партию), `_still_relevant`
  перед закрытием (для `CANDIDATE_DATA_CHANGED` заново `needs_profile_rebuild` из E5-02),
  `dry_run=True` → `DONE` без реального AI-вызова, `dry_run=False` → `FAILED` с
  `NotImplementedError` (реальный клиент — E6/E7, не этого шага) + `backoff(attempts)`
  (5/10/20/40... минут). `src/sfera_ai/scheduler.py` — `run_tick`/`build_scheduler` по
  скелету `03_TDD.md` (`BackgroundScheduler`, `CronTrigger(hour='8,15,19')`,
  `max_instances=1`, тик = detection E5-03 + `process_batch`); не покрыт юнит-тестами
  (обвязка APScheduler), только `import` проверен. Новые настройки в `config.py`:
  `ai_processing_dry_run` (default `True`), `ai_analysis_max_concurrent_jobs` (default `5`).
  Зависимость `apscheduler==3.11.3` (`uv add apscheduler`). Тесты
  `tests/services/test_job_processing.py` — 5 (пустая очередь без AI-вызовов, dry-run →
  DONE, dry-run выключен → FAILED без тихого прохождения, упавшая джоба не блокирует
  остальные, экспонента backoff). Полный сьют `uv run pytest` — 77 passed, регрессий нет.
  Дальше — `step-E5-05-stuck-jobs.md`.
- `2026-08-27` — шаг `step-E5-03-job-creation.md` выполнен частично:
  `detect_and_enqueue(session, platform_base)` в `src/sfera_ai/services/job_detection.py`.
  Реализованы 3 reason: `NEW_HH_LEAD` (новый `headhunter_hhnegotiationrecord` без профиля),
  `NEW_APPLICATION` (новый `courses_application` без профиля и без связанного HH-лида),
  `CANDIDATE_DATA_CHANGED` (объединяет `NEW_ANSWER`/`NEW_RESUME`/`NEW_VIDEO` — на уровне
  детекции доступен только общий bool-флаг `needs_profile_rebuild`, без разбора источника;
  решение владельца). Конверсия HH-лида в Application — через `promote_hh_lead_to_application`
  (E2), без отдельной джобы на сам переход. `VACANCY_PROFILE_CHANGED`/`FEEDBACK_APPLIED`
  отложены — тот же гэп E6/E7, что в `step-E5-02-change-detection.md`. `MANUAL`/`BACKFILL`
  вне scope детекции. Найден и исправлен баг: без проверки «есть ли уже любая активная
  джоба у профиля» повторный тик дублировал `CANDIDATE_DATA_CHANGED` поверх свежесозданной
  `NEW_HH_LEAD` (профиль ещё не пересобран → `sources_snapshot` не совпадает → снова
  «устарело»); тест `test_no_new_jobs_on_repeat_tick_without_changes` поймал это до коммита.
  Тесты `tests/services/test_job_detection.py` — 6 passed. Полный сьют `uv run pytest` —
  72 passed, регрессий нет. Дальше — `step-E5-04-scheduler-dry-run.md`.
- `2026-08-27` — шаг `step-E5-02-change-detection.md` выполнен частично:
  `needs_profile_rebuild(platform_base, profile)` в `src/sfera_ai/services/change_detection.py`
  (+ `CHANGE_DETECTION_TABLES` в `platform_db.py`), тесты `tests/services/test_change_detection.py`
  (3). `needs_fit_recalc` отложен — зависит от `CandidateVacancyAnalysis` (E6-02) и
  `VacancyMemory` (E7-01), которых ещё нет в коде; решение владельца — не забегать
  вперёд по эпикам, реализовать эту функцию на своих шагах E6/E7. Проверено по всем
  `epics/*` — единственный такой разрыв в графе зависимостей. Полный сьют
  `uv run pytest` — 66 passed, регрессий нет. Дальше — `step-E5-03-job-creation.md`.
- `2026-08-27` — шаг `step-E5-01-model-migration.md` выполнен: модель `AIProcessingJob`
  (`src/sfera_ai/models/ai_processing_job.py`), ревизия `0004`
  (`migrations/versions/0004_ai_processing_job.py`), тесты
  `tests/models/test_ai_processing_job.py` (3). `course_id` без SQLAlchemy `ForeignKey`
  в модели (как у `VacancyProfile.course_id`) — `courses_course` не в `Base.metadata`,
  FK на неё только в raw-миграции. Partial UniqueConstraint
  `(candidate_profile_id, course_id, reason) WHERE status IN ('PENDING','PROCESSING')` —
  partial unique index в миграции (аналог `uq_vacancy_profile_course_current`), не в
  ORM-модели (SQLite не поддерживает `postgresql_where`). Upgrade head применён на
  staging через `./scripts/tunnel-platform-db.sh`; полный цикл upgrade+downgrade
  проверен отдельно на одноразовой SQLite-БД, staging не даунгрейдился.
  Полный сьют `uv run pytest` — 63 passed, регрессий нет. Эпик E5 не завершён — дальше
  `step-E5-02-change-detection.md`.
- `2026-08-27` — шаг `step-E4-03-facts-adapter.md` выполнен, эпик E4 завершён:
  `video_facts_from_transcript(job)` в `services/video_facts.py` — один факт-объект из
  `TranscriptionJob.summary_text` по схеме `03_TDD.md` (`key="video_summary"`,
  `confidence="MEDIUM"`, `evidence` с `source_type="VIDEO"`), `job is None`/пустой
  `summary_text` → `[]`. Никакого обращения к видеофайлу/S3 — только текстовые поля уже
  отфильтрованного (`status="DONE"`) джоба из E4-02. TDD (RED→GREEN), 3 новых теста,
  полный сьют 60 passed. Следующий шаг — эпик E5.
- `2026-08-27` — шаг `step-E4-02-reflection.md` выполнен: владелец реализовал и раскатал
  модель `TranscriptionJob` в `sfera_backend` (по согласованию — только шаг 01 внешнего
  плана, без остального пайплайна), гейт E4-01 снят. `VIDEO_FACTS_TABLES` в `platform_db.py`,
  `get_transcript_for_answer` в `services/video_facts.py` — TDD (RED→GREEN), 3 теста, полный
  сьют 57 passed. Прод-смоук нашёл и закрыл реальный блокер: `ai_readonly` не имел `GRANT
  SELECT` на новую платформенную таблицу — выдан отдельным грантом (владелец разрешил).
  Следующий шаг — E4-03 (что бы это ни было по `05_EPICS.md`) либо E5.
- `2026-08-27` — шаг `step-E4-01-readiness-gate.md` выполнен: `TranscriptionJob` не
  реализован в `sfera_backend` (`grep -r "TranscriptionJob" --include="*.py"
  FullSphera/sfera_backend/` — 0 совпадений; `PLATFORM_video-transcription-plan/01_STATE.md`
  — все шаги 00–10 `TODO`, реализация не начата). Блокер зафиксирован в разделе «Внешние
  гейты / блокеры». E4-02/03 переносятся. Следующий разблокированный шаг — эпик E5
  (`AIProcessingJob`+очередь), без источника видео до готовности `TranscriptionJob`.
- `2026-08-27` — шаг `step-E3-05-dry-run-cache.md` выполнен, эпик E3 завершён:
  `process_resume` (`src/sfera_ai/services/resume_pipeline.py`) — оркестрация
  fetch → sniff mime (magic bytes, не расширение — `extract_text` не знает про
  `source_type`) → `extract_text` → `run_resume_extraction`. Идемпотентность на
  уровне сервиса: DONE-запись по `source_answer_id`/`(candidate_profile_id,
  hh_resume_id)` возвращается без единого HTTP/LLM вызова; если упал только
  LLM-шаг (`raw_text` уже заполнен) — ретраится только LLM, fetch не повторяется.
  CLI `src/sfera_ai/cli/run_resume_pipeline.py` — ручной прогон по HH_RESUME (свежие
  `hh_negotiation_id` в первую очередь: старые давали 404 от бэкенда — привязаны к
  уже сменившемуся HH-коннекту). `tests/services/test_resume_pipeline.py` — 6 тестов.
  Полный сьют `uv run pytest` — 54 passed. **Реальный прогон** (свой SSH-туннель к
  staging `db`+`backend` через `ai_shared`, туннель не закоммичен — под вопросом
  владельца, нужен ли постоянно): 10 живых HH-резюме, 9 DONE + 1 FAILED (502 —
  транзиентная ошибка самого HH API), повторный прогон тех же 10 — 0 новых HTTP/LLM
  вызовов (те же `extract_id`), `structured_data` вменяемые на ручной сверке.
  Детали — журнал `step-E3-05-dry-run-cache.md`.
- `2026-08-27` — шаг `step-E3-04-llm-structuring.md` выполнен: TDD-циклом (RED→GREEN)
  добавлены `src/sfera_ai/providers.py` (`OpenRouterClient`/`LLMResult`/
  `LLMProviderError` — единый тонкий клиент для всех LLM-вызовов пайплайна, переиспользуется
  E6/E7) и `src/sfera_ai/services/resume_extraction.py` (`run_resume_extraction` —
  PENDING → вызов LLM → DONE+`structured_data` или FAILED, не пишет частичный результат).
  Невалидный JSON и недоступный провайдер — раздельные ветки FAILED (`error` = сырой ответ
  либо текст ошибки провайдера, обрезаны до 2000 символов). `provider`/`model`/
  `prompt_version` пишутся в строку `ResumeExtract`; токены/latency логируются на каждом
  вызове через `logging` — в самой модели `ResumeExtract` нет колонок под них (в отличие от
  `CandidateVacancyAnalysis`, у которой они есть по `03_TDD.md` разделу 2) — расхождение
  DoD-формулировки с реальной схемой, решено логированием без изменения модели. Тесты
  `tests/test_providers.py` (3, httpx.MockTransport, без реальной сети) и
  `tests/services/test_resume_extraction.py` (3) — полный сьют 48 passed, регрессий нет.
  Добавлен `openrouter_api_key`/`openrouter_base_url` в `config.py` — владелец вписал
  реальный ключ в `.env` сам (агенту запрещено читать/писать файлы с секретами).
- `2026-08-27` — шаг `step-E3-03-text-extraction.md` выполнен: `extract_text`
  (`src/sfera_ai/services/resume_text_extraction.py`) — `pypdf`/`python-docx`,
  `TextExtractionError` на битый файл/неподдерживаемый mime. Тест
  `tests/services/test_resume_text_extraction.py` — 5 passed, полный сьют 42 passed,
  регрессий нет. Детали и обоснование (legacy `.doc` не поддержан, разбиение
  ответственности FAILED-перевода на следующий шаг) — журнал step-файла.
- `2026-08-26` — эпик E2 (`CandidateProfile` identity resolver) реализован — модель,
  Alembic 0002, `resolve_or_create_candidate_profile` с защитой от гонки,
  `promote_hh_lead_to_application`, backfill-скрипт. Миграция и backfill реально
  прогнаны на проде (`step-E2-07-apply-migration-prod.md`) — таблица
  `ai_candidate_profile` создана, 3461 профиль (3310 с HH-привязкой, 1270 с
  заявкой, 1119 пересечений корректно слиты). По пути на проде исправлены три
  инфраструктурные проблемы, не связанные с кодом самой миграции: контейнер БД
  отключился от сети `ai_shared` (переподключён), в `.env` разработчика были
  плейсхолдеры вместо реальных прод-паролей (пароли `ai_owner`/`ai_readonly`
  сброшены заново), не хватало `GRANT REFERENCES`/`GRANT SELECT` на таблицы
  платформы для служебных ролей AI-сервиса (выданы). Детали — журнал
  `step-E2-07-apply-migration-prod.md`. Доска статусов: `E2-01` отмечен `DONE`.
  Следующий шаг — эпик E3 (`ResumeExtract` пайплайн).
- `2026-08-26` — шаг `step-E2-05-transition.md` выполнен: `promote_hh_lead_to_application`
  (`src/sfera_ai/services/candidate_transition.py`) — одна `UPDATE` строка по
  `hh_negotiation_id` с условием `application_id IS NULL`, без `INSERT`; возвращает
  `bool` (была ли строка обновлена). Тест `tests/services/test_candidate_transition.py`
  — 2 passed, без изменений от черновика в шаге. Коммит `71ef56a`. Эпик E2 не
  завершён — дальше следующие шаги (`epics/E2-candidate-identity-resolver/`).
- `2026-08-26` — шаг `step-E2-04-resolve-or-create.md` выполнен:
  `resolve_or_create_candidate_profile` (`src/sfera_ai/services/candidate_identity.py`) —
  два входа `NEW_HH_LEAD`/`NEW_APPLICATION`, для `NEW_APPLICATION` проверяет через
  reflection обратную связь `HHNegotiationRecord.application_id`, чтобы не создать
  дубль `CandidateProfile`. `_insert_or_resolve_race` резолвит `IntegrityError` от
  параллельной вставки в выигравшую строку. **Найден и исправлен пробел в шаге:**
  `platform_base.metadata.bind` не существует в SQLAlchemy 2.0.52 (`MetaData.bind`
  убран) — `reflect_platform_tables` (`platform_db.py`) теперь кладёт
  `base.engine = engine` явным атрибутом, сервис берёт `platform_base.engine`. Тест
  `tests/services/test_candidate_identity.py` — 4 passed, полный сьют 18 passed,
  регрессий нет. Коммит `d26f595`. Эпик E2 не завершён — дальше следующие шаги
  (`epics/E2-candidate-identity-resolver/`).
- `2026-08-26` — шаг `step-E2-03-alembic-revision-0002.md` выполнен: ревизия
  `migrations/versions/0002_ai_candidate_profile.py` (`down_revision='0001'`) — таблица
  `ai_candidate_profile` с двумя FK (`ondelete='CASCADE'`) на
  `courses_application`/`headhunter_hhnegotiationrecord`, `CheckConstraint` якоря, self-FK
  `superseded_by_id → ai_candidate_profile.id` (`ondelete='SET NULL'`) — добавлен сверх
  черновика в шаге, т.к. модель E2-02 эту колонку требует. `-x sqlalchemy.url=...` на
  SQLite не сработал (тот же баг env.py, что в E1-05) — использован `alembic upgrade
  head --sql`, DDL проверен визуально, ошибок нет. Реальное применение на прод — E2-07.
  Коммит `2ba937c`. Эпик E2 не завершён — дальше `step-E2-04-resolve-or-create.md`.
- `2026-08-26` — шаг `step-E2-02-candidate-profile-model.md` выполнен: модель
  `CandidateProfile` (`src/sfera_ai/models/candidate_profile.py`) — оба FK-якоря
  (`application_id`, `hh_negotiation_id`) простые `Integer`, unique, nullable, без
  `ForeignKey()` (платформенные таблицы только reflected); `CheckConstraint` — хотя бы
  один якорь заполнен. Тест `tests/models/test_candidate_profile.py` — 3 passed, полный
  сьют 14 passed, регрессий нет. Коммит `240ad27`. Эпик E2 не завершён — дальше
  `step-E2-03-alembic-revision-0002.md`.
- `2026-08-26` — шаг `step-E2-01-extend-reflection.md` выполнен: тест
  `test_reflect_platform_tables_includes_hh_negotiation_record` добавлен
  (`tests/test_platform_db.py`), прошёл без изменений функции — `reflect_platform_tables`
  уже общая. Добавлена константа `IDENTITY_RESOLVER_TABLES = ("courses_application",
  "headhunter_hhnegotiationrecord")` в `src/sfera_ai/platform_db.py`. `uv run pytest
  tests/test_platform_db.py -v` — 2 passed. Коммит `11c238b`. Эпик E2 не завершён —
  дальше следующие шаги эпика (см. `05_EPICS.md`/`epics/E2-candidate-identity-resolver/`).
- `2026-08-26` — шаг `step-E1-10-state-update.md` выполнен: эпик E1 (`VacancyProfile`)
  реализован — модель, Alembic 0001, versioning-сервис, CLI. Доска статусов: `E1-01`
  отмечен `DONE`. Следующий шаг — эпик E2 (`CandidateProfile` identity resolver).
- `2026-08-26` — шаг `step-E1-09-apply-migration-prod.md` выполнен (владелец дал явное
  разрешение и SSH root-доступ к VPS 5.42.120.39). БД найдена автоматически: контейнер
  `sfera-staging-db-1` (Postgres 17), `POSTGRES_DB=sfera_db`, сеть `ai_shared`. Роль
  `ai_owner` создана, пароль сгенерирован `openssl rand`, в git не коммитился, передан
  владельцу, локальная копия удалена. **Найден и исправлен пробел в шаге:** FK на
  `courses_course` требует `GRANT REFERENCES` — без него первый `alembic upgrade head`
  падал `InsufficientPrivilege` (транзакция откатилась, прод не пострадал); грант добавлен
  в предпосылки step-файла на будущее. Повторный прогон — `ai_vacancy_profile` создана
  (`Running upgrade -> 0001`). CLI-проверка на реальном `course_id=2`: `create`/
  `show-current` вернули `version=1, is_current=true`. Туннель и socat-proxy контейнер
  снесены после проверки.
- `2026-08-26` — шаг `step-E1-08-cli.md` выполнен: CLI `vacancy-profile
  create/show-current/list` (`src/sfera_ai/cli/vacancy_profile.py`) поверх
  `create_vacancy_profile_version`. Тест `tests/cli/test_vacancy_profile_cli.py` —
  1 passed, полный сьют 10 passed, регрессий нет. Коммит `7da8fb1`.
- `2026-08-26` — шаг `step-E1-07-versioning-service.md` выполнен:
  `create_vacancy_profile_version` (`src/sfera_ai/services/vacancy_profile.py`) — снимает
  `is_current` со старой версии через `session.flush()` до `INSERT` новой (порядок flush
  для partial unique index), инкрементит `version`. Тесты `tests/services/test_vacancy_profile.py`
  — 2 passed, полный сьют 9 passed, регрессий нет. Коммит `20ade28`.
- `2026-08-26` — шаг `step-E1-06-write-session.md` выполнен: `src/sfera_ai/db/session.py`
  (`make_session_factory`, `make_write_engine`) по шагу без изменений. `uv run pytest`
  — 7 passed, регрессий нет.
- `2026-08-26` — шаг `step-E1-05-alembic-revision-0001.md` выполнен: ревизия
  `migrations/versions/0001_ai_vacancy_profile.py` — `upgrade` создаёт `ai_vacancy_profile`
  с FK `course_id → courses_course.id` (`ondelete='CASCADE'`) и partial unique index
  `uq_vacancy_profile_course_current` (гарантия ровно одного `is_current=True` на course).
  `revision id` заменён с автосгенерированного hash на `0001`. Синтаксическая проверка на
  SQLite не сработала (`env.py` игнорирует `-x`, всегда берёт `write_database_url`,
  порт 5434 из E1-01 уже снесён) — использован запасной путь из шага, `alembic upgrade
  head --sql` — DDL сгенерирован и проверен визуально, без ошибок. Реальное применение
  на прод — отдельно на E1-09, с подтверждением владельца.
- `2026-08-26` — шаг `step-E1-04-vacancy-profile-model.md` выполнен: модель `VacancyProfile`
  (`src/sfera_ai/models/vacancy_profile.py`) — поля по TDD, `UniqueConstraint(course_id,
  version)`, `course_id` — простой `Mapped[int]` без `ForeignKey` (FK-констрейнт будет в
  Alembic-миграции E1-05 через raw DDL). Тест шага скорректирован: добавлен `updated_at` в
  ожидаемые columns (`TimestampMixin` даёт `created_at`+`updated_at` вместе, отдельного
  created_at-only варианта нет) — решение согласовано с владельцем. `uv run pytest` — 6
  passed, регрессий нет.
- `2026-08-26` — эпик E1 начат: `step-E1-02-write-database-url.md` и
  `step-E1-03-declarative-base.md` выполнены первыми (`step-E1-01-alembic-init.md`
  фактически зависит от них), затем `step-E1-01-alembic-init.md` (код). `Settings`
  получил `write_database_url`, добавлены `sfera_ai/db/base.py` (`Base`,
  `TimestampMixin`), alembic инициализирован (`env.py` читает `Settings`/`Base`).
  Коммиты `7586075`, `ef4cc07`, `ac26c0a`. `.env.example` не обновлён — под глобальным
  запретом чтения/правки агента, владелец добавит `WRITE_DATABASE_URL` сам. Проверка
  `uv run alembic current` пройдена на разовом локальном Postgres (Docker, порт 5434,
  снесён после теста) — не прод. Шаги `E1-01`/`E1-02`/`E1-03` отмечены `DONE` в своих
  step-файлах. Реальный `WRITE_DATABASE_URL` для прода (роль `ai_owner`) — на шаге
  `E1-09`, отдельная прод-операция с явным разрешением владельца.
- `2026-08-26` — реальный прогон E0-04/E0-05 на проде выполнен (владелец дал явное
  разрешение на прод-операцию). Перед изменением схемы снят полный `pg_dump -Fc` бэкап
  `sfera_db` (сохранён локально в `.../scratchpad/backups/`, временная копия на VPS
  удалена). Роль `ai_readonly` создана строго по DDL из `step-E0-04-ssh-tunnel.md`
  (её не было — подтвердил владелец), пароль сгенерирован `openssl rand`, отдан
  владельцу, в git не коммитился. Туннель — временный socat-proxy контейнер в сети
  `ai_shared` на VPS + `ssh -L` с локальной машины (снесён по завершении). Smoke-test
  на `application_id=1`: `OK: read Application id=1`, `OK: write correctly rejected
  (read-only role confirmed)`. Прямой `psql` от `ai_readonly` подтвердил то же: SELECT
  проходит, INSERT — `permission denied for table courses_application`. Прод не
  пострадал, ничего лишнего не удалено/не изменено кроме создания роли. Детали — в
  журналах `step-E0-04-ssh-tunnel.md` и `step-E0-05-smoke-test.md`.
- `2026-08-26` — шаг `step-E0-08-state-update.md` выполнен: эпик E0 (bootstrap)
  реализован — uv-проект, env-конфиг, reflection, smoke-test, Dockerfile, общая
  docker-сеть. `E0-01` в доске статусов отмечен `DONE`. Текущий следующий шаг —
  эпик E1 (`VacancyProfile`).
- `2026-08-26` — шаг `step-E0-07-shared-docker-network.md` выполнен. Владелец дал
  SSH-доступ к VPS и подтвердил прод-операцию отдельно от общего согласия 2026-08-25.
  На VPS: `docker network create ai_shared`, `db` backend'а подключён к ней (правка
  `docker-compose.staging.yml` в `sfera_backend`, коммит `e22bf9b`, запушено в
  `origin/main` после rebase на чужой коммит `edfc20f`). **Инцидент:** после
  пересоздания `db` контейнер `scheduler` не восстановил закэшированное Django DB-
  соединение (`OperationalError: server closed the connection unexpectedly` каждые
  15-30с) — DNS и свежие соединения работали нормально, проблема только в уже открытом
  соединении долгоживущего процесса; исправлено `docker compose restart scheduler`,
  дальше без ошибок. `backend`/`gateway` не пострадали (HTTP 200 всё время). Сетевая
  связность подтверждена: `pg_isready -h db` из контейнера на `ai_shared` → OK.
  `docker-compose.yml` AI-сервиса создан в `SFERA-AI`, коммит `df01000`. Полный разбор
  инцидента — в журнале `step-E0-07-shared-docker-network.md`.
- `2026-08-26` — шаг `step-E0-06-dockerfile.md` выполнен: `Dockerfile` (multi-stage, uv)
  + `.dockerignore` созданы. При сборке всплыл баг: `pyproject.toml` объявляет
  `readme = "README.md"`, но README.md не копировался до финального `uv sync --frozen
  --no-dev`, сборка падала на `Building sfera-ai @ file:///app` с `failed to open file
  /app/README.md`. Исправлено — README.md добавлен в первый `COPY`. После фикса
  `docker build -t sfera-ai:bootstrap .` проходит без ошибок. Коммит `99908c2`.
- `2026-08-26` — шаг `step-E0-05-smoke-test.md` выполнен частично: `src/sfera_ai/smoke_test.py`
  реализован (читает `Application` по id, проверяет что write через `ai_readonly` падает
  с `DBAPIError`). Коммит `721dc6f`. **Не выполнено:** ручной прогон на реальном проде —
  на вопрос о статусе роли `ai_readonly` владелец ответил «без понятия», решено
  реализовать код и отложить прогон до момента, когда роль/туннель будут подтверждены.
- `2026-08-26` — шаг `step-E0-04-ssh-tunnel.md` выполнен частично: `scripts/tunnel-platform-db.sh`
  и `docs/LOCAL_DEV.md` готовы. Т.к. `03_TDD.md` фиксирует общую docker-сеть `ai_shared`
  без публикации `db` на host VPS, туннель — в два прыжка: временный socat-proxy
  контейнер в `ai_shared` на VPS + `ssh -L` поверх него (владелец подтвердил вариант).
  Коммит `d6a140e`. **Не сделано:** создание роли `ai_readonly` на прод-Postgres (DDL
  в step-файле) — вне доступа агента, требует владельца перед стартом E0-05.
- `2026-08-26` — шаг `step-E0-03-reflection-module.md` выполнен: `reflect_platform_tables`
  (SQLAlchemy automap, `MetaData.reflect(only=[...])`) ограничен переданным списком
  таблиц, тест `tests/test_platform_db.py` зелёный (sqlite in-memory, без реальной БД).
  Коммит `4cbcfb4` (смешан с docs-правками предыдущего шага — не критично).
- `2026-08-26` — шаг `step-E0-02-env-config.md` выполнен: `Settings` (pydantic-settings)
  читает `PLATFORM_DATABASE_URL` из окружения/`.env`, тест `tests/test_config.py`
  зелёный, `.env.example` создан (плейсхолдеры, без реального пароля). Коммит `5522817`.
- `2026-08-26` — шаг `step-E0-01-project-scaffold.md` выполнен: uv установлен (brew,
  0.12.6), `uv init --package` (src-layout), добавлены sqlalchemy/psycopg[binary]/
  pydantic-settings + dev pytest, `uv.lock` создан, `py.typed`/`tests/__init__.py`
  добавлены. `uv run python -c "import sfera_ai"` проходит. Коммит `40073bf`.
- `2026-08-25` — репозиторий создан, архитектура и справочные материалы перенесены из
  `FullSphera` (единый `ARCHITECTURE.md`, `PLATFORM_AUDIT_REFERENCE.md`,
  `PLATFORM_video-transcription-plan/`).
- `2026-08-25` — по образцу монорепо `SFERA-Tools` (`project-context/<tool>/` +
  шаблон PRD→CONTEXT→TDD→EPICS→STATE) реструктурирован план: единый `ARCHITECTURE.md`
  разобран на `project-context/sfera-ai/{00_START_HERE,01_PRD,02_CONTEXT,03_TDD,05_EPICS,04_STATE}.md`
  + `step-TEMPLATE.md`. Старые `ARCHITECTURE.md`/`00_STATE.md` в корне `project-context/`
  удалены — содержимое полностью перенесено, потерь нет.
