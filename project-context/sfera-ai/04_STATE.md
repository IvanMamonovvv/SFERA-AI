# STATE — где мы остановились

> **Единственный источник правды о прогрессе.** Обновляй после каждого шага.
> Новый чат: читай сверху вниз, бери первый шаг со статусом `TODO`.

**Проект/фича:** SFERA-AI — AI-анализ кандидатов, единственный инструмент этого репозитория
**Последнее обновление:** `2026-09-06` — найдены и исправлены **три реальных бага**,
обнаруженных владельцем на живых кандидатах course_id=39, плюс пересчитан курс:

1. **CLI без туннеля на резюме** — первый прогон 2026-09-02 использовал внутренний
   docker-адрес backend вместо туннеля, резюме не учлось ни у кого (известный DNS-баг
   E10-01/E11). Исправлено запуском с `HH_BACKEND_BASE_URL=http://localhost:8001`.
2. **Порог `fit_score > threshold`** (строго больше) отсекал кандидатов ровно на
   пороге — исправлено на `>=` в `run_full_course_screening.py:198,207`.
3. **Баг слияния фактов резюме** (`candidate_facts.py:139`, найден на реальном
   кандидате Петрусевич Е.Д.) — `build_or_update_candidate_facts` пропускал
   пересборку `profile.facts`, если платформенный снапшот не менялся, **даже если
   `ResumeExtract` только что стал `DONE` после ретрая** (снапшот не знает про
   статус нашего резюме-пайплайна). Итог: у части кандидатов резюме реально было
   обработано (`status=DONE`), но в `facts` не попадало — оценка шла без него.
   Исправлено: пересборка теперь происходит и когда есть необработанные `DONE`-факты
   резюме, даже без изменения платформенного снапшота. Регрессионный тест добавлен.
4. **Портрет вакансии для course_id=39 был не тот** (id=4, "Портрет от владельца,
   2026-08-31") — описывал ивент/MICE-агентство ("живые мероприятия и музыка",
   "работа без CRM"), а не реальную роль (B2B-продажи хим сырья/техноменклатуры,
   Bitrix — плюс). Не код-баг — неверные входные данные. Владелец прислал правильный
   портрет + ссылку на HH-вакансию (2026-09-06) — пересобран через
   `vacancy_profile create-from-portrait`, новый `VacancyProfile` id=5, версия 2,
   `is_current=true`.

**Пересчёт course_id=39 после всех фиксов** (90 кандидатов, реальный прогон на
проде, туннели через `ssh sfera`/`ssh sfera-ai` — алиасы в `~/.ssh/config`, .env-скрипты
`tunnel-*.sh` содержат устаревший `VPS_HOST`/порт 22, чинить отдельно): `resume_status`
`OK` 80/`MISSING` 8/`FAILED` 2 (легитимный `502` от HH). `recommendation`:
`POSSIBLE_MATCH` 71, `NOT_ENOUGH_DATA` 10, `NOT_A_MATCH` 4, `STRONG_MATCH` 3,
`WEAK_MATCH` 2. **33 кандидата** прошли порог `fit_score>=75` (было 2 на предыдущем
ошибочном портрете) — карточки в zip (scratchpad, не в проекте). Петрусевич Е.Д.
(candidate_profile_id 2398) теперь `fit_score=75, POSSIBLE_MATCH, resume_status=OK` —
корректно учтена. Побочно замечено: при сборке zip-архива резюме Петрусевич не
приложилось ("резюме не найдено") несмотря на `ResumeExtract.status=DONE` —
`collect_export_files`/`archive.py`, похоже, не переиспользует уже сохранённый
резюме-экстракт для вложения файла; не расследовано, не блокирует основной результат
(оценка верна), справедливо для будущего шага.

Также по ходу (в рамках этой же сессии): убран "AI-анализ кандидата" из заголовка
PDF-карточки, добавлен словарь `FACT_KEY_LABELS_RU` в `ai_card.py` — известные ключи
фактов (`full_name`, `sales_segment` и т.д.) отображаются по-русски, незнакомые — как есть.

Следующий шаг — не определён владельцем, ждать новую задачу. Отдельно стоит почистить
`tunnel-platform-db.sh`/`tunnel-backend.sh` (устаревший `VPS_HOST`/порт в `.env`,
сейчас работает только ручной обход через ssh-алиасы `sfera`/`sfera-ai`).

`2026-09-01` — шаг `step-E12-01-cyrillic-font.md` выполнен,
**эпик E12 полностью завершён**. На PyPI нет готового пакета с TTF-шрифтом с кириллицей —
шрифт DejaVu Sans (regular+bold, официальный релиз 2.37, свободная лицензия) вендорен
напрямую в `src/sfera_ai/services/export/fonts/` (~1.4 МБ), зарегистрирован в `ai_card.py`
через `pdfmetrics.registerFont`, все `fontName="Helvetica*"` заменены. По ходу найдена и
исправлена смежная регрессия — первая колонка таблицы критериев рендерилась голой строкой
без стиля Paragraph и брала дефолтный Helvetica; добавлен явный `FONTNAME` на тело таблицы.
Визуально проверено (PDF→PNG на синтетических кириллических данных) — весь текст читаем.
Dockerfile/pyproject.toml не менялись — шрифт копируется вместе с `src/`. Тесты —
`pytest tests/services/test_ai_card_export.py` 8 passed. Детали — журнал
`step-E12-01-cyrillic-font.md`.

`2026-09-01` — шаг `step-E11-02-reverify-borderline-candidates.md`
выполнен: постоянный CLI-флаг `--candidate-ids` в `run_full_course_screening.py`, реальный
прогон на 6 погранично прошедших кандидатах course_id=39 через тунели E11-01+db-туннель.
Побочно найдено и починено: `sfera-staging-backend-1` **снова** отвалился от сети
`ai_shared` (тот же баг, что и в E11-01/раньше) — переподключён `docker network connect`
(согласованное исключение по CLAUDE.md). После починки резюме реально скачались и
учлись (`ai_resume_extract.status=DONE`). Результат: `data_completeness` остался `PARTIAL`
у всех 6 (у них в принципе доступны только 2 из 4 типов источников — не баг), но оба
`STRONG_MATCH`-кандидата (2378, 3026) при учёте реального резюме понизились до
`POSSIBLE_MATCH` — сигнал, что резюме реально меняет вывод модели. Сравнительная таблица
показана владельцу. Решение о пересборке всего 90-прогона курса 39 — отдельный шаг, не
принято в рамках этого. Детали — журнал `step-E11-02-reverify-borderline-candidates.md`.
Ранее в тот же день — шаг `step-E11-01-backend-http-tunnel.md` выполнен
(`scripts/tunnel-backend.sh`, DoD подтверждён ручной проверкой). Ещё раньше — на
реальном прогоне E10-01 (course_id=39,
«РТХ Менеджер по продажам B2B») найдены два новых пробела, заведены отдельными эпиками
**E11** (resume-extraction не работает при ручном прогоне с локальной машины — backend
резолвится только изнутри docker-сети VPS, DNS-ошибка; весь прогон 90 кандидатов прошёл
без резюме, только по анкете) и **E12** (в PDF AI-карточки кириллица рендерится чёрными
прямоугольниками — `Helvetica` без поддержки кириллицы). Оба — `TODO`, план шагов готов,
реализация не начата (ждёт «начинай» от владельца). Детали — `epics/E11-backend-tunnel-verification/`,
`epics/E12-pdf-cyrillic-fix/`.

В тот же день реально использован E10-02 (создан `VacancyProfile` id=4 для `course_id=39`
из портрета владельца) и выданы два новых грантa `ai_readonly`: `testchecks_question`
(планово, для E10-01) и `headhunter_vacancycoursemapping` (ad-hoc, для сверки числа
кандидатов на курсе — платформенный UI показывает заявки+HH-лиды вместе, БД считает их
раздельно). Также найдено и починено: `db` и `backend` контейнеры на VPS отвалились от
сети `ai_shared` (см. `03_TDD.md`, раздел «Инфраструктура и сеть», «Известная
нестабильность») — переподключены вручную.

`2026-08-31` — шаг **E10-02** (портрет кандидата + ссылка на
вакансию → `VacancyProfile`, CLI `create-from-portrait`) выполнен, эпик **E10** полностью
завершён. Детали — журнал `step-E10-02-vacancy-profile-from-portrait.md`.

`2026-08-31` — шаг **E10-01** (полный прогон вакансии по всем
кандидатам курса, CLI) выполнен: код готов, полный сьют зелёный; реальный прогон на
проде ещё не запускался — ждёт `GRANT SELECT` на `testchecks_question` и подтверждения
`course_id`/порога владельцем. Детали — журнал `step-E10-01-full-course-screening.md`.

`2026-08-31` — шаг **E9-04** (стилизация AI-карточки под
визуал ai-screening-hub) выполнен по прямому запросу владельца, поверх уже
завершённого roadmap E0–E9. Детали — журнал `step-E9-04-styled-candidate-card.md`.

`2026-08-31` — шаг **E9-03** выполнен, **эпик E9 (Export)
и весь roadmap E0–E9 полностью завершены**. Формат согласован с владельцем: zip на
несколько кандидатов, `POST .../export/` (`src/sfera_ai/api/routes/export.py`),
подпапка на кандидата (`card.pdf`/`resume.<ext>`/`video.mp4`, недоступное —
`manifest.txt`). Детали — журнал `step-E9-03-export-endpoint.md`.

`2026-08-28` — шаг **E9-01** (AI-карточка PDF, сервисный слой) выполнен по прямому
запросу владельца. `05_EPICS.md` помечал E9 «по запросу, после появления UI» — этот
шаг взят раньше UI по явному указанию.

`2026-08-28` — эпик **E7 (Vacancy Feedback/Memory workflow) полностью завершён**
(шаг `E7-04`, триггер пересчёта fit).

`2026-08-28` — эпик **E6 (Fit scoring) полностью завершён**.
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

**Эпик E13 полностью завершён** (E13-01, E13-02, 2026-09-02). Полный пересчёт
`course_id=39` (90 кандидатов, с реальным учётом резюме через тунели) выполнен на
проде 2026-09-02 — детали в блоке «Последнее обновление» выше. Следующая задача не
определена, ждать от владельца. Эпики **E10**/**E11**/**E12 полностью завершены**
(2026-08-31/2026-09-01).

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
| E7-01 | `VacancyFeedback`/`VacancyMemory` модели + Alembic (`step-E7-01-models.md`) | DONE | 2026-08-28 |
| E7-02 | Интерпретация фидбека LLM (`step-E7-02-interpretation.md`) | DONE | 2026-08-28 |
| E7-03 | Approve workflow Feedback → Memory (`step-E7-03-approve.md`) | DONE | 2026-08-28 |
| E7-04 | Триггер пересчёта fit (`step-E7-04-recalc-trigger.md`) | DONE | 2026-08-28 |
| E8-01 | Веб-слой сервиса, каркас (`step-E8-01-framework-scaffold.md`) | DONE | 2026-08-28 |
| E8-02 | `summary`/`candidates` список (`step-E8-02-summary-list.md`) | DONE | 2026-08-28 |
| E8-03 | Карточка кандидата + история версий (`step-E8-03-candidate-detail-history.md`) | DONE | 2026-08-28 |
| E8-04 | `vacancy-profile`/`feedback` CRUD + approve (`step-E8-04-vacancy-feedback-crud.md`) | DONE | 2026-08-28 |
| E8-05 | `reanalyze` (`step-E8-05-reanalyze.md`) | DONE | 2026-08-28 |
| E9-01 | AI-карточка PDF (`step-E9-01-ai-card-pdf.md`) | DONE | 2026-08-28 |
| E9-02 | Оригинал резюме + видеовизитка (`step-E9-02-resume-video-bundle.md`) | DONE | 2026-08-28 |
| E9-03 | Export-эндпоинт (`step-E9-03-export-endpoint.md`) | DONE | 2026-08-31 |
| E9-04 | Стилизация AI-карточки (`step-E9-04-styled-candidate-card.md`) | DONE | 2026-08-31 |
| E10-01 | Полный прогон вакансии по всем кандидатам, CLI (`step-E10-01-full-course-screening.md`) | DONE (код) | 2026-08-31 |
| E10-02 | Портрет + ссылка на вакансию → VacancyProfile, CLI (`step-E10-02-vacancy-profile-from-portrait.md`) | DONE | 2026-08-31 |
| E11-01 | HTTP-туннель к backend для локального dev (`step-E11-01-backend-http-tunnel.md`) | DONE | 2026-09-01 |
| E11-02 | Пересборка fit-score погранично прошедших кандидатов с реальным резюме (`step-E11-02-reverify-borderline-candidates.md`) | DONE | 2026-09-01 |
| E12-01 | Кириллица в PDF AI-карточки (`step-E12-01-cyrillic-font.md`) | DONE | 2026-09-01 |
| E13-01 | Приоритет резюме в промпте fit-scoring (`step-E13-01-resume-priority-prompt.md`) | DONE | 2026-09-02 |
| E13-02 | Флаг «нет резюме» в CSV/PDF/API (`step-E13-02-resume-missing-flag.md`) | DONE | 2026-09-02 |

## Журнал (дополнять, не стирать)

- `2026-09-01` — шаг `step-E11-02-reverify-borderline-candidates.md` выполнен,
  **эпик E11 полностью завершён**. Владелец выбрал постоянный CLI-флаг
  `--candidate-ids` (не одноразовый scratch-скрипт) — `run_full_course_screening.py`:
  `_screen_profile`/`_screen_candidate_profile_id` вынесены из `_screen_application`
  без дублирования (резюме/facts/fit-scoring логика общая). Первый прогон на 6
  кандидатах провалился новой ошибкой (`Server disconnected without sending a
  response.`) — не DNS из E11-01. Расследование по ssh на VPS (`docker logs`,
  `docker top`, `docker inspect`) нашло причину: `sfera-staging-backend-1` снова
  отвалился от сети `ai_shared` (та же нестабильность, что чинилась в E11-01/
  раньше, `03_TDD.md` «Известная нестабильность» — переподключение не пережило
  рестарт/пересоздание контейнера). Починено `docker network connect ai_shared
  sfera-staging-backend-1` (согласованное исключение CLAUDE.md — общая
  docker-сеть). После этого повторный прогон реально скачал и обработал резюме
  всех 6 (`ai_resume_extract.status=DONE`). Результат: `data_completeness` остался
  `PARTIAL` у всех (у этих кандидатов доступны только 2 из 4 типов источников —
  не баг формулы, а факт данных), но оба `STRONG_MATCH` (candidate_profile_id
  2378, 3026) при учёте реального резюме понизились до `POSSIBLE_MATCH` — резюме
  реально меняет вывод модели. Сравнительная таблица показана владельцу.
  Побочная мелкая находка (не расследовалась/не чинилась): у candidate_profile_id
  2378 в финальной версии `fit_score=NULL` при валидном остальном ответе LLM;
  также `ResumeExtract.error` не очищается при повторном успешном прогоне после
  `FAILED` (текст старой ошибки остаётся в БД у `status=DONE` записей). Тунели
  остановлены штатно после прогона, proxy-контейнеры на VPS не остались висеть.
  Решение о пересборке всего 90-прогона курса 39 с резюме — НЕ принято в рамках
  этого шага, отдельный вопрос владельцу. Детали — журнал
  `step-E11-02-reverify-borderline-candidates.md`.
- `2026-09-01` — шаг `step-E11-01-backend-http-tunnel.md` выполнен: новый
  `scripts/tunnel-backend.sh` по паттерну `tunnel-platform-db.sh` — socat-proxy на
  VPS в сети `ai_shared` (backend-контейнер:8000 → 127.0.0.1:18000), локальный
  `ssh -L localhost:8001 -> proxy`. Отдельные порты/имя proxy-контейнера
  (`ai-backend-tunnel-proxy`) от db-туннеля — оба можно держать поднятыми
  одновременно. `.env`/`config.py` не тронуты — подмена `HH_BACKEND_BASE_URL`
  только через переменную окружения при ручном прогоне. Ручная проверка всех
  трёх DoD: идемпотентность (второй запуск при поднятом туннеле — сразу exit 0,
  без дублирования), `cleanup()` trap (после завершения ssh-процесса локальный
  порт закрывается, `docker rm -f` на VPS отрабатывает без ошибок), `HHClient.
  _authenticate()` через туннель реально получил токен от backend. Код не
  менялся, только новый скрипт — тестов нет (shell-скрипт, не Python).
- `2026-08-31` — шаг `step-E10-02-vacancy-profile-from-portrait.md` выполнен, эпик
  **E10 полностью завершён**: зависимость `beautifulsoup4`,
  `build_vacancy_requirements(portrait_text, source_url, *, llm_client)` в новом
  `services/vacancy_portrait.py` — скачивание+вычистка `source_url` через `httpx`+
  `BeautifulSoup` (ошибка скачивания не блокирует, продолжает по портрету), один
  LLM-вызов (`response_format=json_object`), невалидный JSON/не-объект →
  `InvalidVacancyRequirementsResponse` до создания `VacancyProfile`, `source_url`
  кладётся в итоговый JSON ключом `source_url` (без миграции схемы — `requirements`
  уже свободный JSON). Новая подкоманда `vacancy-profile create-from-portrait`
  (`--course-id`, ровно один из `--portrait-text`/`--portrait-file`, опционально
  `--source-url`/`--notes`) переиспользует `create_vacancy_profile_version` как есть
  (уже триггерит `enqueue_fit_recalc_for_course`). Тесты —
  `tests/services/test_vacancy_portrait.py` (5). Полный сьют `uv run pytest` —
  183 passed, регрессий нет.
- `2026-08-31` — шаг `step-E10-01-full-course-screening.md` выполнен: `RESUME_DETECTION_TABLES`
  (`platform_db.py` = `CANDIDATE_FACTS_TABLES` + `testchecks_question`),
  `find_anketa_resume_answer_id(platform_base, candidate_id)` в `resume_pipeline.py` —
  закрывает гэп из E3/E5 («анкетное резюме» = `Answer` с
  `question.question_text == "ANKETA_RESUME"`, join `testchecks_testattempt` по
  `candidate_id`, последний по `answered_at`). Новый CLI
  `src/sfera_ai/cli/run_full_course_screening.py`: обходит все `Application` курса
  (по образцу `run_fit_scoring_sample.py::_application_ids_for_course`),
  `resolve_or_create_candidate_profile` → резюме (hh_negotiation_id →
  `process_resume(hh_resume_id=...)`, иначе `find_anketa_resume_answer_id` →
  `process_resume(source_answer_id=...)`, ни того ни другого — пропуск без падения) →
  `build_or_update_candidate_facts` → `run_fit_scoring`; try/except на кандидата (по
  паттерну `_run_sample`); CSV/stdout-сводка на всех; zip карточек только для
  `fit_score > --fit-threshold` (default 75) через уже готовый
  `build_candidates_export_archive` (E9-03/E9-04). Тесты —
  `tests/services/test_resume_pipeline.py` (+2). Полный сьют `uv run pytest` —
  178 passed, регрессий нет. Автотеста на сам CLI-скрипт нет — по прецеденту
  `run_fit_scoring_sample.py`/`run_resume_pipeline.py`. **Реальный прогон на проде НЕ
  выполнялся** — нужен новый `GRANT SELECT` на `testchecks_question` для `ai_readonly`
  и подтверждение владельцем `course_id`/порога непосредственно перед запуском (реальные
  LLM-вызовы, реальные деньги — прецедент E6-04/E6-05).
- `2026-08-31` — шаг `step-E9-04-styled-candidate-card.md` выполнен: `ai_card.py`
  пересобран на `Table`-блоках reportlab (визуал как в ai-screening-hub — чёрная
  плашка, синий подзаголовок, блок рекомендации с акцентной полосой, два столбца
  сильные стороны/что уточнить, серый блок платформы, таблица баллов с цветом по
  порогу, `KeepTogether` — одна страница на кандидата). `full_name` — из последнего
  `ResumeExtract.status="DONE".structured_data["full_name"]`, `_SYSTEM_PROMPT` в
  `resume_extraction.py` дополнен этим полем. `candidate_display_name` получил
  опциональный `full_name`-параметр (обратная совместимость с `archive.py`,
  который не менялся — вне периметра шага). `CONFIDENCE_RU`-маппинг сверен с
  `fit_scoring.py` (`LOW/MEDIUM/HIGH`) — не менялся. Тесты — `test_ai_card_export.py`
  (8, было 4). Полный сьют `uv run pytest` — 176 passed, регрессий нет.
- `2026-08-28` — шаг `step-E9-02-resume-video-bundle.md` выполнен:
  `collect_export_files(session, platform_base, candidate_profile_id, *, hh_client, s3_client,
  s3_bucket) -> dict` в `src/sfera_ai/services/export/files.py`. Резюме — переиспользует готовый
  `fetch_resume_bytes` (E3-02) на последнем `ResumeExtract(status="DONE")` кандидата. Видео —
  join `testchecks_answer` → `testchecks_testattempt` → `testchecks_transcriptionjob`
  (`status="DONE"`) по `candidate_id` (переиспользован `get_candidate_id` из E5-02), затем
  скачивание `Answer.file` через S3. Оба блока результата — `{"available": bool, "bytes": ...}`,
  ошибка `S3 get_object` (видео удалено через 30 дней) ловится, не падает — `available: False`,
  export продолжается без файла. Тесты `tests/services/test_export_files.py` — 4. Полный сьют
  `uv run pytest` — 166 passed, регрессий нет.
- `2026-08-28` — шаг `step-E9-01-ai-card-pdf.md` выполнен. `render_ai_card_pdf(session,
  candidate_profile_id, course_id) -> bytes | None` в
  `src/sfera_ai/services/export/ai_card.py` — рендерит текущую версию
  `CandidateVacancyAnalysis` (summary/strengths/risks/gaps) + `CandidateProfile.facts`
  через `reportlab` (чистый Python, без cairo/pango — легче для Docker на staging).
  `None`, если для кандидата нет текущей версии анализа. Веб-роут не добавлялся — шаг
  только сервисный слой, по TDD. Тесты — `tests/services/test_ai_card_export.py` (3:
  полные данные / частичные / нет анализа). Зависимость `reportlab` добавлена в
  `pyproject.toml` через `uv add`.
- `2026-08-28` — шаг `step-E8-05-reanalyze.md` выполнен, **эпик E8 (Read API)
  полностью завершён**. `POST .../candidates/{id}/reanalyze/`
  (`src/sfera_ai/api/routes/candidates.py`) проверяет кандидата через
  `get_candidate_detail` (404), ставит `AIProcessingJob(reason=MANUAL)` через новую
  `enqueue_manual_reanalyze` (`src/sfera_ai/services/job_detection.py`). Rate-limit —
  5 минут на кандидата (порог подтверждён владельцем), по времени создания последней
  MANUAL-джобы (не по активным статусам — ручная джоба к повторному клику обычно уже
  DONE); повтор в окне → 429. Тесты — `tests/api/test_reanalyze.py` (3, TDD). Полный
  сьют `uv run pytest` — 159 passed, регрессий нет. Следующий по графу — E9 (Export),
  но не начинать: он «по запросу, после появления UI».
- `2026-08-28` — шаг `step-E8-04-vacancy-feedback-crud.md` выполнен: `GET/POST
  .../vacancy-profile/`, `GET/POST .../feedback/`, `POST .../feedback/{id}/approve/`
  (`src/sfera_ai/api/routes/vacancy.py`). POST `vacancy-profile/` переиспользует
  `create_vacancy_profile_version` (E1), POST `feedback/` синхронно вызывает
  `interpret_feedback` (E7-02), `approve/` — `approve_feedback` (E7-03, сам триггерит
  пересчёт fit из E7-04). Повторный approve → 409, неизвестный id/чужой course → 404,
  невалидное тело (Pydantic) → 422. Общие FastAPI-зависимости вынесены в новый
  `src/sfera_ai/api/deps.py` (использует и `candidates.py`, без изменения поведения);
  `create_app()` получил `llm_client_factory`. Тесты — `tests/api/test_vacancy_endpoints.py`
  (14, TDD: сначала RED — 404 без роутов, потом реализация). Полный сьют `uv run pytest`
  — 156 passed, регрессий нет. Следующий шаг — `step-E8-05-reanalyze.md`.
- `2026-08-28` — шаг `step-E8-03-candidate-detail-history.md` выполнен:
  `GET .../candidates/{candidate_profile_id}/` и `.../history/`
  (`src/sfera_ai/api/routes/candidates.py`, `src/sfera_ai/services/api_read.py`).
  `get_candidate_detail` — все версии `CandidateVacancyAnalysis` по candidate+course,
  пусто → `None` → 404; `current` (полный набор полей, включая evidence/strengths/risks),
  `facts` из `CandidateProfile.facts`, сжатая `history` (`id`/`version`/`fit_score`/
  `analyzed_at`/`changed` — какие поля изменились относительно предыдущей версии).
  `get_candidate_history` — полный список версий с `input_snapshot_diff`
  (человекочитаемо: только реально изменившиеся ключи, `{key: {old, new}}`).
  Тесты — `tests/api/test_candidate_detail.py` (5). Полный сьют `uv run pytest` —
  145 passed, регрессий нет. Детали — журнал step-файла.
- `2026-08-28` — шаг `step-E8-02-summary-list.md` выполнен: `GET .../summary/` и
  `GET .../candidates/` (`src/sfera_ai/api/routes/candidates.py`,
  `src/sfera_ai/services/api_read.py`). `{course_uuid}` из URL резолвится в платформенный
  `Course.id` через reflection (`platform_db.API_READ_TABLES`); неизвестный `course_uuid`
  → 404. `summary` — total/processed/queued/errors по `AIProcessingJob`/
  `CandidateVacancyAnalysis`, без похода в платформенные `Application`. `candidates` —
  offset-пагинация (`limit`/`offset`, `limit≤200`), контрактные поля включая `fit_delta`
  (версия vs версия-1) и `demo_progress` (своя копия формулы `Progress.completed_lessons/
  total_lessons*100` — третья копия в системе, осознанное решение владельца, т.к.
  AI-сервис не может импортировать Django-код платформы). `create_app()` — новый параметр
  `platform_engine_factory`. Тесты — `tests/api/test_candidates_list.py` (7). Полный сьют
  `uv run pytest` — 140 passed, регрессий нет. Детали — журнал step-файла.
- `2026-08-28` — шаг `step-E8-01-framework-scaffold.md` выполнен: фреймворк FastAPI
  (`src/sfera_ai/api/app.py`, `create_app(*, engine_factory, bff_shared_secret=None)`),
  `/health` (реальный `SELECT 1` через движок, не заглушка). `app = create_app()` НЕ на
  уровне модуля — uvicorn запускается factory-режимом
  (`uvicorn sfera_ai.api.app:create_app --factory`), иначе `Settings()` падала бы на
  любом импорте модуля без полного `.env`. `src/sfera_ai/api/routes/__init__.py` —
  пустой `APIRouter(prefix="/api/v1/courses/{course_uuid}/ai-analysis")` по `03_TDD.md`
  (эндпоинты — следующие шаги E8). Auth — shared-secret заголовок
  `X-BFF-Shared-Secret` (`src/sfera_ai/api/auth.py`), новое required-поле
  `Settings.bff_shared_secret`; `.env`/`.env.example` под запретом правки агента —
  владелец дописал `BFF_SHARED_SECRET` в `.env` (2026-08-28). `Dockerfile` CMD
  заменён с временного `smoke_test` на реальный uvicorn-entrypoint. Тесты
  `tests/api/test_health.py` (2) + `tests/api/test_auth.py` (3). Ручная проверка —
  сервер поднят локально, `curl localhost:8123/health` → `{"status":"ok"}` HTTP 200.
  Полный сьют `uv run pytest` — 133 passed, регрессий нет. Открытый пункт вне
  scope: подключение BFF-прокси SPHERA (`SPHERA/src/app/api/proxy/`) к AI-сервису
  ещё не сделано — существующий прокси проксирует только к `sfera_backend`,
  отдельная задача во фронтенд-репозитории. Следующий шаг — `step-E8-02`
  (`epics/E8-read-api/`).
- `2026-08-28` — шаг `step-E7-04-recalc-trigger.md` выполнен, **эпик E7 (Vacancy
  Feedback/Memory workflow) полностью завершён**: `enqueue_fit_recalc_for_course(session,
  course_id)` в `src/sfera_ai/services/job_detection.py` — ставит `AIProcessingJob
  (reason=VACANCY_PROFILE_CHANGED)` на все `CandidateVacancyAnalysis.is_current` этого
  `course`, переиспользуя дедупликацию `_create_job_if_absent` (E5-03). Расширен
  `_create_job_if_absent` параметром `course_id` — раньше не участвовал ни в проверке
  дублей, ни в создании джобы (для профильных reason это было не нужно, всегда `None`,
  но для вакансийных джоб `course_id` обязателен явно — см. `job_processing.py`).
  Хуки подключены прямым вызовом (без событий/сигналов) в двух местах: конец
  `approve_feedback` (`vacancy_memory.py`) и конец `create_vacancy_profile_version`
  (`vacancy_profile.py`), оба после своего `commit()`. Тесты —
  `tests/services/test_recalc_trigger.py` (3). Полный сьют `uv run pytest` —
  128 passed, регрессий нет. Следующий шаг — эпик **E8** (Read API), по графу
  зависимостей `05_EPICS.md` (`E1, E2, E6, E7 → E8`).
- `2026-08-28` — шаг `step-E7-03-approve.md` выполнен: `approve_feedback(session,
  feedback, approved_by, weight_hint=None)` в `src/sfera_ai/services/vacancy_memory.py` —
  маппинг сентимента на `weight_hint` (`NEGATIVE`→`PENALIZE`, `POSITIVE`→`BOOST`,
  `NEUTRAL`→`INFO_ONLY`, явный параметр перекрывает). `rule_text` из
  `feedback.ai_suggested_rule` (E7-02). Одна транзакция:
  `VacancyMemory(is_active=True)` + `feedback.applied=True`. Повторный approve —
  `FeedbackAlreadyAppliedError` (явная ошибка, не no-op). Тесты
  `tests/services/test_vacancy_memory_approve.py` — 5. Полный сьют `uv run pytest` —
  125 passed, регрессий нет. Следующий шаг — `step-E7-04-recalc-trigger.md`.
- `2026-08-28` — шаг `step-E7-02-interpretation.md` выполнен:
  `interpret_feedback(feedback, llm_client)` в `src/sfera_ai/services/feedback_interpretation.py`
  (промпт `text`+`sentiment` → короткое правило, `gpt-4o-mini` через `OpenRouterClient`,
  `prompt_version="feedback-interpretation-v1"`). Решение зафиксировано: вызов
  **синхронный**, не через `AIProcessingJob` — дешёвый, отдельная очередь не оправдана.
  `LLMProviderError` перехватывается внутри сервиса, `ai_suggested_rule` остаётся `""`
  без падения запроса (DoD п.2). Эндпоинт создания `VacancyFeedback`, который будет
  вызывать этот сервис, ещё не написан — вне scope этого шага (следующие шаги эпика
  E7). Тесты `tests/services/test_feedback_interpretation.py` — 2 (успешный вызов с
  парсингом промпта, ошибка провайдера → пустая строка). Полный сьют `uv run pytest` —
  120 passed, регрессий нет.
- `2026-08-28` — шаг `step-E7-01-models.md` выполнен: модели `VacancyFeedback`
  (`src/sfera_ai/models/vacancy_feedback.py`) и `VacancyMemory`
  (`src/sfera_ai/models/vacancy_memory.py`), одна ревизия `0007` на обе таблицы
  (`migrations/versions/0007_ai_vacancy_feedback_memory.py`) — по прецеденту 0005.
  `course_id`/`author_id`/`approved_by_id` — платформенные FK (`courses_course`,
  `users_customuser`), без `ForeignKey()` в ORM-модели, констрейнт только в raw-миграции
  (паттерн `AIProcessingJob`/`CandidateVacancyAnalysis`); `candidate_profile_id`
  (CASCADE), `analysis_id` (SET NULL), `source_feedback_id` (SET NULL) — внутренние
  `ai_*` FK с `ForeignKey()`. Индексы `(course_id, applied)` и `(course_id, is_active)`.
  Тесты `tests/models/test_vacancy_feedback.py`/`test_vacancy_memory.py` — 8 (constraints,
  индексы, CASCADE/SET NULL поведение на SQLite с `PRAGMA foreign_keys=ON`). Новый GRANT:
  `GRANT REFERENCES ON users_customuser TO ai_owner` — первый раз для этой таблицы
  (см. [[project_grant_references_pattern]]), выдан на staging через VPS+`docker exec`.
  Upgrade head применён на staging через туннель (`0006`→`0007`), downgrade проверен
  только на SQLite `tmp_engine` (правило — не даунгрейдить shared staging). Полный
  сьют `uv run pytest` — 118 passed, регрессий нет. Следующий шаг — `step-E7-02` (по
  `epics/E7-feedback-workflow/`, если есть) либо эпик E8.
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
