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
- [ ] `epics/E7-feedback-workflow/step-E7-01-models.md` — `VacancyFeedback` +
  `VacancyMemory` модели + Alembic.
- [ ] `epics/E7-feedback-workflow/step-E7-02-interpretation.md` — LLM-интерпретация
  фидбека → `ai_suggested_rule`.
- [ ] `epics/E7-feedback-workflow/step-E7-03-approve.md` — approve workflow
  (Feedback → Memory), оба сентимента (BOOST/PENALIZE).
- [ ] `epics/E7-feedback-workflow/step-E7-04-recalc-trigger.md` — триггер пересчёта
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

## Граф зависимостей

E0 → E1, E2, E4
E1, E2 → E5
E2 → E3
E1, E2, E5 → E6 (E4 — опциональный вход: если ещё не готов, видео-факты просто
  отсутствуют в `CandidateProfile.facts`, `data_completeness` ниже; E6 не блокируется)
E1 → E7
E1, E2, E6, E7 → E8
E6, E8 → E9
