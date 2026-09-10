# EPICS — карта эпиков

> Эпик = крупный блок работы (обычно один слой или одна связная возможность). Эпик
> разбивается на атомарные шаги, каждый — на одну сессию. Цепочка: PRD → эпики (здесь)
> → шаг-план → прогресс в `04_STATE.md`. Порядок и содержание — перенесены без
> изменений из раздела S бывшего единого `ARCHITECTURE.md` (2026-08-21).
>
> Один формат для всех эпиков: `epics/E{n}-<slug>/step-E{n}-NN-<slug>.md` по шаблону
> `step-TEMPLATE.md`. Для E0-E2 шаги содержат полный TDD-контент (RED-GREEN-REFACTOR,
> код) — перенесены из ранее отдельного формата `docs/plans/` (2026-08-26), второй
> путь больше не используется.

## Карта

| Эпик | Название | Зависит от | Риск |
|---|---|---|---|
| E0 | Инфраструктура сервиса (bootstrap, Dockerfile, reflection smoke-test) | — | нулевой |
| E1 | `VacancyProfile` (модель + Alembic 0001, ручной CRUD) | E0 | нулевой |
| E2 | `CandidateProfile` identity resolver | E0 | низкий |
| E3 | `ResumeExtract` пайплайн (S3/HH API + LLM extraction) | E2 | средний |
| E4 | Интеграция с `TranscriptionJob` (видео) | E0 | зависит от чужого пайплайна |
| E5 | `AIProcessingJob` + свой APScheduler-процесс (dry-run) | E1, E2 | низкий |
| E6 | Fit scoring (`CandidateVacancyAnalysis`) | E1, E2, E5 | средний-высокий (первый платный AI-вызов в проде) |
| E7 | Vacancy Feedback/Memory workflow | E1 | низкий |
| E8 | Read API для будущего UI | E1, E2, E6, E7 | низкий |
| E9 | Export (по запросу, после появления UI) | E6, E8 | — |
| E10 | Ручной прогон вакансии + сборка портрета из ссылки (CLI, demo без UI) | E6, E9 | средний (реальные LLM-вызовы на всех кандидатах вакансии) |
| E13 | Приоритет источников (резюме > ответы > видео) + видимость «нет резюме» | E6, E9, E10 | низкий-средний (меняет промпт fit-scoring, версия промпта) |
| E14 | Реализация видео-транскрибации в `sfera_backend` (внешний код, трекинг из SFERA-AI) | E4 | требует явного разрешения владельца на каждый шаг — другой репозиторий |
| E15 | «Обработка кандидатов» — модалка HR-скрининга по портрету вакансии (SFERA-AI + `sfera_backend` + `SPHERA`) | E6, E8, E9 | часть шагов в других репозиториях — явное разрешение на каждый |
| E16 | Деплой сервиса на VPS — ai-scheduler отдельным процессом (был не задеплоен), deploy-скрипт по образцу backend/frontend | E0 | нулевой (только SFERA-AI, инфра) |
| E17 | Точность карточки — приоритет резюме над платформенными полями, склейка резюме в один PDF | E9, E13 | низкий-средний (меняет `_platform_block`/экспорт, известный баг вложения резюме) |
| E18 | Шедулер реально обрабатывает резюме — сейчас `process_resume` вызывается только вручную из CLI, автопайплайн его не знает | E3, E5 | средний (меняет обработчик очереди; шаг B/C — retry сетевых ошибок HH + авто-ретрай FAILED, шаг C с Alembic-миграцией) |

## Разбивка на шаги

### E0 — Инфраструктура сервиса
- [ ] `epics/E0-service-bootstrap/step-E0-01-project-scaffold.md` — uv-проект, src-layout.
- [ ] `epics/E0-service-bootstrap/step-E0-02-env-config.md` — env-конфиг (pydantic-settings).
- [ ] `epics/E0-service-bootstrap/step-E0-03-reflection-module.md` — SQLAlchemy `automap`
  reflection на 2-3 таблицах (`courses_application`, `testchecks_answer`).
- [ ] `epics/E0-service-bootstrap/step-E0-04-ssh-tunnel.md` — SSH-туннель для локальной
  разработки (скрипт + документация).
- [ ] `epics/E0-service-bootstrap/step-E0-05-smoke-test.md` — smoke-test: читает 1
  реальную запись `Application` по id.
- [ ] `epics/E0-service-bootstrap/step-E0-06-dockerfile.md` — Dockerfile (multi-stage, uv).
- [ ] `epics/E0-service-bootstrap/step-E0-07-shared-docker-network.md` — общая
  docker-сеть с backend (`03_TDD.md`, «Инфраструктура и сеть») — ⚠️ затрагивает прод.
- [ ] `epics/E0-service-bootstrap/step-E0-08-state-update.md` — обновить `04_STATE.md`.
  Готово: контейнер поднимается независимо от `backend`/`scheduler`, читает
  платформенные данные, ничего не меняет.

### E1 — `VacancyProfile`
- [ ] `epics/E1-vacancy-profile/step-E1-01-alembic-init.md` — Alembic инициализация.
- [ ] `epics/E1-vacancy-profile/step-E1-02-write-database-url.md` — `write_database_url`
  в Settings.
- [ ] `epics/E1-vacancy-profile/step-E1-03-declarative-base.md` — Declarative Base +
  timestamp mixin.
- [ ] `epics/E1-vacancy-profile/step-E1-04-vacancy-profile-model.md` — модель
  `VacancyProfile`.
- [ ] `epics/E1-vacancy-profile/step-E1-05-alembic-revision-0001.md` — Alembic-ревизия
  0001.
- [ ] `epics/E1-vacancy-profile/step-E1-06-write-session.md` — write-сессия.
- [ ] `epics/E1-vacancy-profile/step-E1-07-versioning-service.md` — versioning-сервис
  (иммутабельные версии, транзакционное переключение `is_current`).
- [ ] `epics/E1-vacancy-profile/step-E1-08-cli.md` — CRUD CLI для ручного заполнения
  (без публичного API).
- [ ] `epics/E1-vacancy-profile/step-E1-09-apply-migration-prod.md` — применить
  миграцию на прод-Postgres — ⚠️ затрагивает прод.
- [ ] `epics/E1-vacancy-profile/step-E1-10-state-update.md` — обновить `04_STATE.md`.
  Готово: можно вручную завести требования вакансии.

### E2 — `CandidateProfile` identity resolver
- [ ] `epics/E2-candidate-identity-resolver/step-E2-01-extend-reflection.md` —
  reflection на `headhunter_hhnegotiationrecord`.
- [ ] `epics/E2-candidate-identity-resolver/step-E2-02-candidate-profile-model.md` —
  модель `CandidateProfile` (без `facts`-логики).
- [ ] `epics/E2-candidate-identity-resolver/step-E2-03-alembic-revision-0002.md` —
  Alembic-ревизия 0002.
- [ ] `epics/E2-candidate-identity-resolver/step-E2-04-resolve-or-create.md` — сервис
  `resolve_or_create_candidate_profile` (`03_TDD.md`, «Candidate Identity»), защита от
  гонки.
- [ ] `epics/E2-candidate-identity-resolver/step-E2-05-transition.md` — функция перехода
  HH Lead → Platform Candidate.
- [ ] `epics/E2-candidate-identity-resolver/step-E2-06-backfill-script.md` — read-only
  backfill-скрипт для первого прогона по существующим
  `Application`/`HHNegotiationRecord` (reflection, не трогает backend).
- [ ] `epics/E2-candidate-identity-resolver/step-E2-07-apply-migration-prod.md` —
  применить миграцию на прод-Postgres — ⚠️ затрагивает прод.
- [ ] `epics/E2-candidate-identity-resolver/step-E2-08-state-update.md` — обновить
  `04_STATE.md`. Готово: по всей базе на каждого кандидата/лида ровно один
  `CandidateProfile`.

### E3 — `ResumeExtract` пайплайн
- [x] `epics/E3-resume-pipeline/step-E3-01-model-migration.md` — модель + Alembic-ревизия.
- [x] `epics/E3-resume-pipeline/step-E3-02-source-fetch.md` — получение файла: S3 Timeweb
  (свои креды `USE_S3_STORAGE`, тот же бакет, что и backend — напрямую через `boto3`)
  или HH API (собственный HTTP-клиент, повторяющий контракт `get_resume_pdf` — код
  backend'а переиспользовать нельзя, разные репозитории).
- [x] `epics/E3-resume-pipeline/step-E3-03-text-extraction.md` — PDF/DOC → `raw_text`.
- [x] `epics/E3-resume-pipeline/step-E3-04-llm-structuring.md` — LLM structured
  extraction, общий `providers.py` клиент (переиспользуется E6/E7).
- [x] `epics/E3-resume-pipeline/step-E3-05-dry-run-cache.md` — сквозной пайплайн,
  прогон на 5–10 реальных резюме из прода. Готово: кэшируется, повторный запуск не
  бьёт HH API дважды по одному `hh_resume_id`.

### E4 — Интеграция с транскрибацией видео
- [ ] `epics/E4-video-integration/step-E4-01-readiness-gate.md` — проверка, реализован
  ли `PLATFORM_video-transcription-plan/` к этому моменту; если нет — шаг блокируется
  до готовности того плана.
- [ ] `epics/E4-video-integration/step-E4-02-reflection.md` — reflection на
  `TranscriptionJob` (то же подключение к БД, что и в E0).
- [ ] `epics/E4-video-integration/step-E4-03-facts-adapter.md` — адаптер
  `summary`→факт-объект для сборки профиля (E6). Готово: `facts` включают видео-факты,
  когда транскрипт готов.

### E5 — `AIProcessingJob` + очередь
- [x] `epics/E5-processing-queue/step-E5-01-model-migration.md` — модель + Alembic-ревизия.
- [x] `epics/E5-processing-queue/step-E5-02-change-detection.md` —
  `needs_profile_rebuild`/`needs_fit_recalc`, чистый SQL, без AI-вызовов
  (`03_TDD.md`, раздел 5).
- [x] `epics/E5-processing-queue/step-E5-03-job-creation.md` — детекция событий →
  постановка джоб по всем 10 `reason`.
- [x] `epics/E5-processing-queue/step-E5-04-scheduler-dry-run.md` — свой
  APScheduler-процесс (`03_TDD.md`, раздел 6), dry-run режим: реальные AI-вызовы
  выключены флагом. Тест: тик быстрый при пустой очереди, детекция не расходует
  AI-бюджет.
- [x] `epics/E5-processing-queue/step-E5-05-stuck-jobs.md` — cron-детектор зависших
  `PROCESSING` джоб.
- [x] `epics/E5-processing-queue/step-E5-06-hh-lead-pii-ttl.md` — TTL-очистка сырого
  текста резюме (`ResumeExtract.raw_text`) для HH-лидов, не конвертировавшихся в
  платформенного кандидата (решение владельца 2026-08-26, `02_CONTEXT.md`). Готово:
  джобы корректно ставятся по всем трём уровням детекции (раздел 5 `03_TDD.md`), PII
  неконвертировавшихся лидов не хранится бессрочно.
- [x] `epics/E5-processing-queue/step-E5-07-merge-detection.md` — детекция
  `CandidateMergeLog` (`03_TDD.md`, «Candidate Identity — Merge кандидатов»), owner
  approved 2026-08-26 (`02_CONTEXT.md`) — пропущено в исходной разбивке E2 при
  архитектурном ревью 2026-08-26, добавлено сюда как часть той же tick-driven detection
  фазы, что `needs_profile_rebuild` (E5-02) — логически выполняется вместе с E5-03
  (постановка джоб), хоть и идёт по номеру после TTL-шага. Хранит собственный глобальный
  курсор `last_seen_merge_log_id` (не привязан к конкретному профилю, в отличие от
  `max_answer_id` в `sources_snapshot`) — решить на этом шаге, где именно хранить (напр.
  отдельная key-value таблица `ai_service_state`). Готово: platform-merge не приводит к
  расхождению двух AI-историй одного человека, `is_superseded`/`superseded_by`
  проставляются корректно.

### E6 — Fit scoring
- [x] `epics/E6-fit-scoring/step-E6-01-profile-assembly.md` — сборка
  `CandidateProfile.facts` из всех источников (резюме/ответы/видео).
- [x] `epics/E6-fit-scoring/step-E6-02-analysis-model.md` — `CandidateVacancyAnalysis`
  модель + Alembic (FK `vacancy_profile` — PROTECT).
- [x] `epics/E6-fit-scoring/step-E6-03-llm-fit-call.md` — реальный LLM Fit-вызов,
  версии, `is_current`.
- [x] `epics/E6-fit-scoring/step-E6-04-queue-integration.md` — включение реальных
  AI-вызовов в очередь (снятие dry-run, первый платный вызов в проде — только на
  ограниченном пилоте, с подтверждением владельца). Диспетчер готов; сам флаг
  `ai_processing_dry_run` для непрерывной автообработки отложен до деплоя планировщика
  (E8) — сознательное решение владельца.
- [x] `epics/E6-fit-scoring/step-E6-05-manual-validation.md` — ручной прогон на 10–20
  реальных кандидатов, сверка адекватности с HR. Готово: `fit_score`+evidence
  сохраняются, повторный прогон без изменений не создаёт новую версию.

### E7 — Vacancy Feedback/Memory workflow
- [x] `epics/E7-feedback-workflow/step-E7-01-models.md` — `VacancyFeedback` +
  `VacancyMemory` модели + Alembic.
- [x] `epics/E7-feedback-workflow/step-E7-02-interpretation.md` — LLM-интерпретация
  фидбека → `ai_suggested_rule`.
- [x] `epics/E7-feedback-workflow/step-E7-03-approve.md` — approve workflow
  (Feedback → Memory), оба сентимента (BOOST/PENALIZE).
- [x] `epics/E7-feedback-workflow/step-E7-04-recalc-trigger.md` — триггер пересчёта
  затронутых `is_current` анализов при новой Memory/VacancyProfile версии. Готово:
  unit на workflow feedback→approve→memory→пересчёт.

### E8 — Read API
- [ ] `epics/E8-read-api/step-E8-01-framework-scaffold.md` — веб-слой сервиса (не
  Django ViewSet) по контракту `03_TDD.md` («API/контракты»), auth между BFF и
  AI-сервисом.
- [ ] `epics/E8-read-api/step-E8-02-summary-list.md` — `summary/` и `candidates/`
  (список).
- [ ] `epics/E8-read-api/step-E8-03-candidate-detail-history.md` — карточка кандидата +
  история версий.
- [ ] `epics/E8-read-api/step-E8-04-vacancy-feedback-crud.md` — `vacancy-profile/` +
  `feedback/` CRUD + approve.
- [ ] `epics/E8-read-api/step-E8-05-reanalyze.md` — ручной `reanalyze/` эндпоинт.
  Отдельно решить, как фронтенд увидит API (BFF-прокси, уже согласовано в
  `02_CONTEXT.md`). Готово: эндпоинты отдают данные, UI не реализуется на этом шаге.

### E9 — Export
- [ ] `epics/E9-export/step-E9-01-ai-card-pdf.md` — AI-карточка PDF (summary/strengths/
  risks + facts).
- [ ] `epics/E9-export/step-E9-02-resume-video-bundle.md` — оригинал резюме +
  видеовизитка (переиспользование `collect_candidate_archive_entries`-подобной логики,
  собственная реализация).
- [ ] `epics/E9-export/step-E9-03-export-endpoint.md` — export-эндпоинт/CLI, формат
  выдачи согласовать с владельцем на момент реализации. По запросу, после появления UI
  выбора кандидатов (`03_TDD.md`, «Future Export»).
- [x] `epics/E9-export/step-E9-04-styled-candidate-card.md` — стилизация AI-карточки
  под визуал ai-screening-hub (reportlab Table-блоки).

### E10 — Ручной прогон вакансии + сборка портрета из ссылки

По прямому запросу владельца (2026-08-31) — проверить бэкенд-логику отбора на реальной
вакансии без фронтенда, до появления UI.

- [ ] `epics/E10-manual-screening/step-E10-01-full-course-screening.md` — CLI:
  все кандидаты вакансии (не выборка) через resume+facts+fit-scoring, zip карточек
  прошедших порог `fit_score > 75`. Требует новую функцию поиска анкетного резюме
  (гэп из E3/E5) и новый `GRANT SELECT` на `testchecks_question`.
- [ ] `epics/E10-manual-screening/step-E10-02-vacancy-profile-from-portrait.md` — CLI:
  портрет кандидата (+опционально ссылка на открытое описание вакансии) → LLM-синтез
  `VacancyProfile.requirements`.

### E11 — Проверка fit-score на реальных резюме (backend-туннель)

По прямому запросу владельца (2026-09-01) — на реальном прогоне E10-01 (course_id=39)
обнаружено, что resume-extraction падает при ручном локальном прогоне (DNS: backend
резолвится только изнутри docker-сети VPS), fit-scoring прошёл только по анкете.

- [ ] `epics/E11-backend-tunnel-verification/step-E11-01-backend-http-tunnel.md` — HTTP-туннель
  к backend-контейнеру с локальной машины (по паттерну `tunnel-platform-db.sh`).
- [ ] `epics/E11-backend-tunnel-verification/step-E11-02-reverify-borderline-candidates.md` —
  пересборка resume+facts+fit для 6 погранично прошедших кандидатов (`fit_score=75`)
  курса 39 с реальным резюме, сравнение «было/стало».

### E12 — Кириллица в PDF-экспорте

Найдено 2026-09-01 на реальной AI-карточке: весь русский текст в PDF рендерится чёрными
прямоугольниками (`Helvetica` не поддерживает кириллицу).

- [x] `epics/E12-pdf-cyrillic-fix/step-E12-01-cyrillic-font.md` — TTF-шрифт с кириллицей
  в `ai_card.py` вместо `Helvetica`.

### E13 — Приоритет источников + видимость «нет резюме»

По прямому запросу владельца (2026-09-01) — резюме важнейший источник данных о
кандидате (связь с кандидатом + опыт), 2-й по значимости — ответы на анкету, 3-й —
видеовизитка. При конфликте значений одного параметра между источниками — верить
резюме. Отсутствие/битое резюме — НЕ hard-block: если ответы+видео в порядке,
менеджер продолжает работать с кандидатом, но нехватка должна быть видна явно, а
итоговая оценка естественно мягче/осторожнее при малом объёме данных. Решение
зафиксировано в памяти — [[project_source_priority_resume_answers_video]].

- [x] `epics/E13-source-priority-visibility/step-E13-01-resume-priority-prompt.md` —
  приоритет резюме > ответы > видео при конфликте фактов, явная инструкция в
  промпте fit-scoring, версия промпта инкрементирована.
- [x] `epics/E13-source-priority-visibility/step-E13-02-resume-missing-flag.md` —
  видимый флаг «резюме отсутствует/битое» в CSV-сводке CLI, PDF-карточке, API
  summary/candidates — не блокирует скоринг, только объясняет менеджеру причину
  меньшей уверенности.

После E13 — пересчитать оставшихся 84 кандидатов курса 39 (course_id=39) одним
прогоном по новой логике (решение владельца 2026-09-01, не дублировать работу
из E11-02).

### E14 — Реализация видео-транскрибации в `sfera_backend`

**Другой репозиторий.** Весь код этого эпика — `sfera_backend`/`SPHERA`, НЕ `SFERA-AI`.
По правилу проекта (`CLAUDE.md`) менять их код нельзя без отдельного явного разрешения
владельца на каждую конкретную правку — эпик здесь только трекает план и порядок, само
согласование шагов из `SFERA-AI` не выдаётся. Полная детальная спецификация каждого шага
(интерфейсы, edge cases, DoD) — в `project-context/PLATFORM_video-transcription-plan/
step-NN-*.md`; шаги ниже — только краткая карта + явное указание где/что делать (не
дублировать содержимое, «один факт — один файл»). Порядок и зависимости между шагами —
`project-context/PLATFORM_video-transcription-plan/EXECUTION_PLAN.md`. Прогресс внешнего
плана (00-01 DONE) — `project-context/PLATFORM_video-transcription-plan/01_STATE.md`,
не дублировать в `04_STATE.md` этого репозитория, только ссылаться.

Решено владельцем (2026-09-07): LLM для summary — `gpt-4o-mini` через прокси; скоуп —
только транскрибация + краткий пересказ содержания, без классификации/вердикта.

- [ ] `epics/E14-video-transcription-worker/step-E14-01-enqueue-on-completion.md` —
  репозиторий `sfera_backend`, `testchecks/views.py`/`perform_create` (или `post_save`
  сигнал) — постановка `TranscriptionJob(PENDING)` при загрузке видеовизитки.
  Детали — `PLATFORM_video-transcription-plan/step-02-enqueue-on-completion.md`.
- [ ] `epics/E14-video-transcription-worker/step-E14-02-transcription-provider.md` —
  репозиторий `sfera_backend`, новый `testchecks/services/transcription/base.py` +
  `LocalFasterWhisperProvider`. Детали —
  `PLATFORM_video-transcription-plan/step-03-transcription-provider.md`.
- [ ] `epics/E14-video-transcription-worker/step-E14-03-summary-provider.md` —
  репозиторий `sfera_backend`, `ProxyLLMProvider` (`gpt-4o-mini`), `SummaryPromptTemplate`.
  Детали — `PLATFORM_video-transcription-plan/step-04-summary-provider.md`.
- [ ] `epics/E14-video-transcription-worker/step-E14-04-worker-command.md` —
  репозиторий `sfera_backend`, `testchecks/management/commands/run_transcription_worker.py`.
  Детали — `PLATFORM_video-transcription-plan/step-05-worker-command.md`.
- [ ] `epics/E14-video-transcription-worker/step-E14-05-api-expose.md` — репозиторий
  `sfera_backend`, сериализатор карточки кандидата + OpenAPI/`03_API.md`. Детали —
  `PLATFORM_video-transcription-plan/step-06-api-expose.md`.
- [ ] `epics/E14-video-transcription-worker/step-E14-06-hr-ui.md` — репозиторий `SPHERA`
  (фронтенд), `src/domains/Candidate/`. Детали —
  `PLATFORM_video-transcription-plan/step-07-hr-ui.md`.
- [ ] `epics/E14-video-transcription-worker/step-E14-07-retention-guard.md` — репозиторий
  `sfera_backend`, `core/scheduler.py::clean_expired_videos`/`check_disk_pressure`.
  Детали — `PLATFORM_video-transcription-plan/step-08-retention-guard.md`.
- [ ] `epics/E14-video-transcription-worker/step-E14-08-tests-smoke.md` — репозиторий
  `sfera_backend`, юнит-тесты + `06_TEST_CHECKLIST.md`. Детали —
  `PLATFORM_video-transcription-plan/step-09-tests-smoke.md`.
- [ ] `epics/E14-video-transcription-worker/step-E14-09-prod-rollout.md` — репозиторий
  `sfera_backend`, `docker-compose`/деплой VPS. Детали —
  `PLATFORM_video-transcription-plan/step-10-prod-rollout.md`. Готово: HR видит
- [ ] `epics/E14-video-transcription-worker/step-E14-10-change-detection-video.md` — репозиторий
  `SFERA-AI` (этот, не `sfera_backend`). Найдено архитектурным ревью 2026-09-07: change detection
  (`compute_current_sources_snapshot`, эпик E5) не замечает готовность `TranscriptionJob` — без
  этого шага видео-факты не попадают в `CandidateProfile.facts`/`fit_score`. Зависит от
  E14-01/02/03.
  транскрипт + пересказ видеовизитки в проде.

### E15 — «Обработка кандидатов» (модалка HR-скрининга)

Дизайн согласован владельцем 2026-09-08, ревью архитектурных рисков проведено —
**`docs/superpowers/specs/2026-09-08-candidate-screening-modal-design.md`** (не
дублировать содержимое сюда, «один факт — один файл»). Заменяет подход, ранее
предполагавшийся частью `step-E14-06-hr-ui.md` («batch-scoring approach») — сам
`E14-06` остаётся про другое (транскрипт видео в карточке одного кандидата), не
пересекается с этим эпиком.

Один эпик, шаги физически в трёх репозиториях (см. дизайн-документ, раздел
«Авторизация и межсервисный вызов») — по аналогии с E14: шаги в `SFERA-AI` без
ограничений, шаги в `sfera_backend`/`SPHERA` требуют отдельного явного разрешения
владельца на каждый конкретный шаг.

**Блок A — SFERA-AI (свой репозиторий):**
- [ ] `epics/E15-candidate-screening-modal/step-E15-01-transfer-model.md` — модель
  `CandidateVacancyTransfer` + Alembic-ревизия, уникальный индекс
  `(candidate_profile_id, course_id)`, upsert обновляет `transferred_at`.
- [ ] `epics/E15-candidate-screening-modal/step-E15-02-enqueue-full-screening.md` —
  `enqueue_full_screening_for_course(session, course_id)` в `job_detection.py`,
  выполняется асинхронно (не в теле HTTP-запроса), дедуп джоб защищён от гонки
  двойного «Сохранить» (partial unique index в БД или гвард на вызывающей стороне).
- [ ] `epics/E15-candidate-screening-modal/step-E15-03-screening-endpoint.md` —
  `GET .../candidates/screening/` (`fit_score >= 60`, сортировка по убыванию,
  `transferred: bool`), фикс отображения `floor(fit_score/10)` вместо `round`.
- [ ] `epics/E15-candidate-screening-modal/step-E15-04-vacancy-profile-trigger.md` —
  `POST .../vacancy-profile/` дополняется вызовом `enqueue_full_screening_for_course`.
- [ ] `epics/E15-candidate-screening-modal/step-E15-05-export-transfer-mark.md` —
  `POST .../export/` проставляет `CandidateVacancyTransfer` только для кандидатов с
  реально собранным `card.pdf`, не для всех id из запроса.

**Блок B — `sfera_backend` (другой репозиторий, разрешение на каждый шаг):**
- [ ] `epics/E15-candidate-screening-modal/step-E15-06-backend-proxy-endpoints.md` —
  новые проксирующие view (по паттерну `CandidateArchiveJob*View`,
  `courses/views.py`) для screening/vacancy-profile/export, защищены существующим
  `CourseCandidatesManagementPermission`.
- [ ] `epics/E15-candidate-screening-modal/step-E15-07-sfera-ai-client.md` — новый
  HTTP-клиент к SFERA-AI (`integrations/sfera_ai/client.py`, по образцу
  `integrations/headhunter/client.py`) + секрет `SFERA_AI_SHARED_SECRET` в
  settings/env (парный к `bff_shared_secret`, уже существующему в SFERA-AI).

**Блок C — `SPHERA` (фронтенд, разрешение на каждый шаг):**
- [ ] `epics/E15-candidate-screening-modal/step-E15-08-hr-ui-modal.md` — кнопка
  «Обработка кандидатов» + модалка (textarea портрета, список, экспорт
  одиночный/массовый), вызывает только проксирующие endpoint'ы блока B, не SFERA-AI
  напрямую.

### E16 — Деплой сервиса на VPS

Найдено 2026-09-09 при обсуждении прод-релиза E15: `docker-compose.yml`/`Dockerfile`
поднимали только `ai-service` (FastAPI/uvicorn) — `scheduler.py` (тик очереди
`AIProcessingJob` раз в 30 минут) нигде не был подключён к деплою, реальные AI-вызовы
без него не начнутся никогда, даже при `ai_processing_dry_run=False`. Один эпик, весь
код — SFERA-AI (без ограничений на разрешение).

- [x] `epics/E16-service-deployment/step-E16-01-scheduler-compose-service.md` — `ai-scheduler`
  отдельным сервисом в `docker-compose.yml`, инвариант «ровно один инстанс».
- [x] `epics/E16-service-deployment/step-E16-02-deploy-script.md` — `scripts/deploy-ai-service.sh`
  по образцу `deploy-backend.sh`/`deploy-frontend.sh` (git pull main → build → migrate → healthcheck).
- [x] `epics/E16-service-deployment/step-E16-03-deployment-doc.md` — `docs/DEPLOYMENT.md`.

### E17 — Точность карточки (резюме приоритетнее платформы) + PDF-резюме

Владелец на реальной карточке (кандидат #2964, `resume_status=FAILED`) поднял два вопроса
2026-09-10: (1) платформенные поля («Данные платформы») — сырые данные, введённые
кандидатом на регистрации, ничем не сверяются с резюме; (2) резюме кандидата сейчас
отдельный файл в ZIP-архиве (E9-03), не приложено к самой карточке. Владелец решил:
резюме подменяет платформенные поля при успешном парсинге (не просто флаг конфликта);
резюме и карточка — один PDF-документ (склейка страниц), не отдельные файлы. Также
всплыл известный баг из журнала `04_STATE.md` (`2026-09-06`, кандидат Петрусевич 2398):
`collect_export_files`/`archive.py` не приложили резюме в ZIP, хотя `ResumeExtract.status
= DONE` — не расследовано, попадает в scope E17-02.

- [x] `epics/E17-card-resume-accuracy/step-E17-01-resume-overrides-platform.md` —
  `_platform_block`/`candidate_facts.py`: поля из `ResumeExtract.structured_data`
  (телефон/город/опыт/должности/компании — не только `full_name`) подменяют
  платформенные при успешном парсинге, платформенное значение остаётся как fallback.
- [x] `epics/E17-card-resume-accuracy/step-E17-02-fix-resume-attach-bug.md` — разобрать и
  починить баг невложения резюме при `ResumeExtract.status=DONE` (кейс Петрусевич 2398).
  Оказался уже закрыт фиксом `company_slug` (`0af0089`, 2026-09-09).
- [x] `epics/E17-card-resume-accuracy/step-E17-03-merge-resume-into-pdf.md` — склейка
  `card.pdf` + резюме в один PDF (`pypdf`), не-PDF резюме — страница-заглушка +
  файл всё равно в ZIP (fallback), замена прежнего поведения ZIP с отдельным
  `resume.<ext>` (E9-03).

### E18 — Шедулер реально обрабатывает резюме

Найдено 2026-09-10 при расследовании бага «Резюме не удалось обработать» в PDF-карточке
(course_id=39, 34/82 резюме упали на обрыве keep-alive соединения с OpenRouter — фикс
retry уже в `main`, коммит `8e1363e`). Побочно найдена более фундаментальная проблема:
автоматический тик шедулера (`scheduler.py::run_tick`, раз в 30 минут) вообще никогда не
вызывает `services/resume_pipeline.py::process_resume` — ни для новых кандидатов, ни
ретраем упавших. `job_processing.py::_run_real_ai_call` вызывает только `run_fit_scoring`
(вакансийные reason'ы) или `build_or_update_candidate_facts` (остальные) — ни один путь
не скачивает/парсит резюме. Резюме сейчас обрабатывается **только** ручным запуском CLI.
Риск, которого боится владелец: кандидат закрывает доступ к резюме на HH раньше, чем
успеваем его скачать. Согласованный с владельцем порядок реализации — по одному шагу,
каждый с отдельным явным «начинай»:

- [x] Шаг A (самое важное, без миграции БД) — вшить вызов `process_resume` в
  `_run_real_ai_call`, чтобы резюме скачивалось/парсилось в течение 30 минут после
  отклика кандидата, а не ждало ручного CLI. Готово, разбит на 3 под-шага
  (последовательная цепочка, каждый со своим DoD), все DONE 2026-09-10:
  - [x] `epics/E18-scheduler-resume-pipeline/step-E18-01a-resume-pipeline-service-extraction.md`
    — вынести `ensure_resume_processed` из CLI в сервисный слой.
  - [x] `step-E18-01b-job-processing-calls-resume-pipeline.md` — `_run_real_ai_call`/
    `process_batch` безусловно вызывают `ensure_resume_processed`; в ветке
    `VACANCY_REASONS` дополнительно фикс facts staleness (найдено ревью-агентом
    2026-09-10, подтверждён владельцем): `build_or_update_candidate_facts` перед
    `run_fit_scoring`, иначе свежескачанное резюме не попадёт в `fit_score`.
  - [x] `step-E18-01c-scheduler-wiring.md` — `scheduler.py::run_tick` собирает
    `hh_client`/`s3_client`, рефлексит `RESUME_DETECTION_TABLES`.
- [x] `step-E18-02-hh-client-retry.md` — (B) один retry на транспортную ошибку в
  `HHClient.get_resume_pdf` (`integrations/hh_client.py`), по образцу уже сделанного
  фикса `providers.py::OpenRouterClient._request_with_retry` (`8e1363e`). DONE 2026-09-10.
- [x] `step-E18-03-failed-resume-requeue.md` — (C, с Alembic-миграцией) отдельный
  крон-джоб для авто-ретрая уже упавших `ResumeExtract.status=FAILED`, по образцу
  `scheduler.py::run_requeue_stuck`/`job_processing.py::requeue_stuck_jobs`. Новые поля
  `attempts`/`retry_after` на `ResumeExtract` + `resume_extract_max_attempts=5` (владелец
  подтвердил), cron раз в 2 часа. DONE 2026-09-10 — эпик E18 закрыт целиком.

### E19 — Ретраи AIProcessingJob

Найдено при разборе бага "100,0/10" в PDF-карточке (см. E20): для `AIProcessingJob` нет ни
потолка попыток, ни авто-ретрая FAILED — в отличие от уже реализованного для `ResumeExtract`
(E18-03). Без этого строгая валидация из E20 превратит "видимый неверный балл" в "кандидат
молча зависает без анализа навсегда" (найдено ревью-агентом 2026-09-10). Предпосылка для E20.

- [x] `epics/E19-ai-job-retry-infra/step-E19-01-max-attempts-config.md` — конфиг
  `ai_processing_job_max_attempts`, проверка/фикс инкремента `attempts`. DONE 2026-09-10.
- [x] `epics/E19-ai-job-retry-infra/step-E19-02-failed-job-requeue.md` — авто-ретрай FAILED
  `AIProcessingJob` с истёкшим `retry_after`, по образцу `run_resume_retry` (E18-03).
  DONE 2026-09-10 — эпик E19 закрыт целиком.

### E20 — Валидация значений criteria_scores

LLM в fit-scoring иногда путает шкалу критерия (0-10) со шкалой `fit_score` (0-100) — модель
кладёт в `criteria_scores` число вроде 100, код это не проверяет, PDF рисует "100,0/10".
Зависит от E19 — без ретрая отклонённый ответ = кандидат без анализа навсегда.

- [x] `epics/E20-criteria-scores-validation/step-E20-01-value-range-validation.md` — строгая
  валидация каждого значения `criteria_scores` (0-10, шаг 0.5) в `_parse_and_validate`,
  отклонение всего ответа при нарушении (не клэмп/деление на 10).
  DONE 2026-09-10 — эпик E20 закрыт целиком.

### E21 — Форматирование отображения баллов в PDF

Балл критерия и итоговый балл в PDF всегда показывались с одним знаком после запятой
(`f"{value:.1f}"`), даже на целых значениях — "10,0/10" вместо "10/10". Независим от E19/E20
по коду, но не чинит уже неверные числа старых записей (только формат).

- [ ] `epics/E21-score-display-formatting/step-E21-01-trim-trailing-zero.md` — убрать хвост
  ",0" на целых значениях, оставить реальный дробный хвост (",5" и т.п.), для критериев и
  итоговой строки "Итог: X/10".

### E22 — Читаемые названия критериев

Ключи `criteria_scores`, которые генерирует LLM, — сырые snake_case-ключи, скопированные
verbatim из `vacancy_profile.requirements` ("опыт_B2B_продаж" вместо "Опыт B2B продаж").
Независим от E19/E20/E21, можно делать параллельно.

- [ ] `epics/E22-readable-criteria-names/step-E22-01-prompt-readable-labels.md` — промпт
  fit-scoring явно требует читаемые русские названия без `_`, `PROMPT_VERSION` →
  `fit-scoring-v4`. Проверено (ревью-агент 2026-09-10): `criteria_scores` нигде не
  используется как программный идентификатор — переименование безопасно.

## Граф зависимостей

E0 → E1, E2, E4
E1, E2 → E5
E2 → E3
E1, E2, E5 → E6 (E4 — опциональный вход: если ещё не готов, видео-факты просто
  отсутствуют в `CandidateProfile.facts`, `data_completeness` ниже; E6 не блокируется)
E1 → E7
E1, E2, E6, E7 → E8
E6, E8 → E9
E6, E9 → E10
E10 → E11
E9 → E12
E6, E9, E10 → E13
E4 → E14 (реализация в sfera_backend, каждый шаг — отдельное разрешение владельца)
E6, E8, E9 → E15 (шаги в sfera_backend/SPHERA — отдельное разрешение владельца на каждый)
E0 → E16 (деплой самого сервиса, весь код в SFERA-AI)
E9, E13 → E17 (точность карточки, весь код в SFERA-AI)
E5 → E19 (ретраи AIProcessingJob, весь код в SFERA-AI)
E6, E19 → E20 (валидация criteria_scores)
E9 → E21 (форматирование баллов в PDF, независим от E19/E20)
E6 → E22 (читаемые названия критериев, независим от E19/E20/E21)
