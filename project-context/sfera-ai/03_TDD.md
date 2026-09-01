# TDD — технический дизайн

> «Как реализуем». Рождается из `01_PRD.md`/`02_CONTEXT.md`. Здесь техника: данные,
> API, слои, риски. Дата исходного анализа — 2026-08-21, решение об отдельном
> сервисе — 2026-08-25 (см. журнал `02_CONTEXT.md`).

## 1. Обзор решения

Отдельный сервис в отдельном репозитории, свой контейнер, свой релиз-цикл, не
зависящий от деплоя `sfera_backend`.

- **Чтение** данных платформы (`Application`, `Progress`, `Answer`,
  `HHNegotiationRecord`, `Course`) — прямое подключение к тому же контейнеру Postgres,
  без Django ORM, через reflection (SQLAlchemy `automap` считывает реальную структуру
  таблиц на старте — в коде AI-сервиса нет ни одного вручную продублированного поля
  платформенной таблицы).
- **Запись** — 7 собственных таблиц (раздел 2), управляются собственными явными
  SQLAlchemy-моделями + Alembic-миграциями (не Django migrations — у сервиса нет Django).
- **БД одна и та же**, физически общий контейнер `db` — как сейчас `backend` и
  `scheduler` оба ходят в один Postgres по внутренней docker-сети. Новый сервис
  подключается туда же, портом наружу БД по-прежнему не торчит.
- **Фоновая обработка** — свой процесс с APScheduler внутри своего контейнера (обычная
  Python-библиотека, не завязана на Django). Celery/Redis не нужны.
- Транскрибация видео — не дублируется: AI-сервис использует уже согласованный (но не
  реализованный) план `PLATFORM_video-transcription-plan/` как внешний read-only
  источник (та же техника reflection), а не как часть себя.

**Технический нюанс privacy-каскада.** FK на платформенные таблицы (`courses_application`,
`courses_course`, `testchecks_answer`, `headhunter_hhnegotiationrecord`) ниже — это
настоящие FK-констрейнты на уровне Postgres, создаваемые Alembic-миграцией AI-сервиса,
а не Django-модели с `on_delete=...`. Раз AI-сервис не Django-приложение, каскад по
152-ФЗ (`hard_delete_user_data` → `user.delete()`) не может сработать «по-питоновски»
через Django ORM-коллектор (Django не знает о существовании этих таблиц). Поэтому там,
где ниже написано `CASCADE`, миграция AI-сервиса обязана явно указать `ON DELETE CASCADE`
в самом DDL (`ForeignKey(..., ondelete='CASCADE')`) — тогда каскад сработает на уровне
самого Postgres в момент, когда Django выполнит финальный `DELETE FROM courses_application ...`,
независимо от того, какой сервис инициировал операцию.

**Риск для будущих миграций `sfera_backend` (найдено при архитектурном ревью,
2026-08-26).** Эти же FK — это зависимость в обратную сторону, о которой `sfera_backend`
не знает: у 4 таблиц платформы (`courses_application`, `courses_course`,
`testchecks_answer`, `headhunter_hhnegotiationrecord`) появляются внешние FK-констрейнты
из другой Postgres-роли (`ai_owner`), вне поля зрения Django-миграций. Обычный `ALTER
COLUMN`/`ADD FIELD` не заметит их, но операция, которую Postgres выполняет через
пересоздание таблицы (несовместимое изменение типа колонки, некоторые сценарии
`ALTER TABLE` с rewrite), может неожиданно упереться в чужой FK. **Coordination-чеклист
перед прод-DDL AI-сервиса (E1-09 и аналогичные шаги в E2+):** перед тем как накатывать
Alembic-миграцию с новым FK на таблицу платформы — свериться, не запланирована ли в
`sfera_backend` в это же окно схемная миграция этой же таблицы. Отдельно: заметку о
самой зависимости стоит перенести и в `sfera_backend` (другой репозиторий, правится
только с явного разрешения владельца на каждую конкретную правку — см. `CLAUDE.md`) —
решение переносить или нет зависит от владельца.

## 2. Сущности / данные

Все модели — собственные SQLAlchemy-модели (declarative, не reflected — этими 7
таблицами владеет сам AI-сервис, схема пишется явно и версионируется через Alembic).
Общие поля `created_at`/`updated_at` — свой маленький mixin в коде сервиса (аналог
`CreatedModifiedBaseModel`, но не переиспользовать чужой — он Django-specific).

### `VacancyProfile`
Структурированные требования заказчика к вакансии (=`Course`).
- `course` — FK → `courses.Course`, CASCADE, `related_name='ai_vacancy_profiles'`
- `version` — PositiveIntegerField
- `is_current` — BooleanField, default False
- `requirements` — JSONField (свободная структура: must_have/strong_plus/acceptable/
  negative_signals/stop_factors/location/salary/travel/experience/industry/skills/
  management/personal_sales — категории не фиксирую в схеме, только в JSON-конвенции
  на уровне сервисного слоя, чтобы менять состав категорий без миграций)
- `notes` — TextField, blank
- `created_by` — FK → `CustomUser`, SET_NULL, nullable
- `created_at` — auto_now_add
- **UniqueConstraint**: `(course, version)`
- **Индекс**: `(course, is_current)`
- **on_delete от Course**: CASCADE
- Versioning: иммутабельные версии, `is_current` переключается транзакцией. Никогда не
  UPDATE `requirements` у существующей версии.

### `VacancyFeedback`
Сырой фидбек менеджера/заказчика по кандидату или по вакансии в целом.
- `course` — FK → `courses.Course`, CASCADE
- `candidate_profile` — FK → `CandidateProfile`, CASCADE, nullable (null = фидбек общий)
- `analysis` — FK → `CandidateVacancyAnalysis`, SET_NULL, nullable
- `author` — FK → `CustomUser`, SET_NULL, nullable
- `text` — TextField
- `sentiment` — CharField choices (`POSITIVE`/`NEGATIVE`/`NEUTRAL`)
- `ai_suggested_rule` — TextField, blank — AI-интерпретация в виде предлагаемого правила
- `applied` — BooleanField, default False
- `created_at` — auto_now_add
- **Индекс**: `(course, applied)`

### `VacancyMemory`
Утверждённое менеджером правило для будущих кандидатов этой вакансии.
- `course` — FK → `courses.Course`, CASCADE
- `rule_text` — TextField
- `weight_hint` — CharField choices (`BOOST`/`PENALIZE`/`INFO_ONLY`)
- `source_feedback` — FK → `VacancyFeedback`, SET_NULL, nullable
- `approved_by` — FK → `CustomUser`, SET_NULL, nullable
- `approved_at` — DateTimeField
- `is_active` — BooleanField, default True
- **Индекс**: `(course, is_active)`
- Не версия `VacancyProfile` — правила подмешиваются в prompt Fit-скоринга (раздел 4),
  не переписывают структурированные требования автоматически.

### `CandidateProfile`
Живой (мутируемый) снепшот фактов о человеке — ядро идентичности.
- `application` — OneToOneField → `courses.Application`, CASCADE, nullable, unique
- `hh_negotiation` — OneToOneField → `integrations.headhunter.HHNegotiationRecord`,
  CASCADE, nullable, unique
- **CheckConstraint**: `application IS NOT NULL OR hh_negotiation IS NOT NULL`
- `facts` — JSONField — каждый факт-объект несёт встроенное evidence:
  `{"key": "...", "value": "...", "confidence": "...", "evidence": [{"source_type": "ANSWER", "source_id": 123, "excerpt": "..."}]}`
- `data_completeness` — CharField choices (`MINIMAL`/`PARTIAL`/`FULL`) либо Integer 0–100
- `sources_snapshot` — JSONField — что использовано для сборки текущей версии (см.
  раздел 5 «Change Detection») — это и есть механизм change detection
- `version` — PositiveIntegerField, default 1
- `built_at` — DateTimeField
- `is_superseded` — BooleanField, default False — профиль вытеснен platform-merge'ем
  (`Application.merged_into`), живая работа больше не идёт через него (см. «Merge
  кандидатов» ниже)
- `superseded_by` — FK → `self`, SET_NULL, nullable — на какой профиль указывает после
  merge, если у выжившего Application свой `CandidateProfile` уже существовал
- **on_delete**: оба FK CASCADE, `CustomUser`-hard-delete автоматически стирает профиль
  через каскад от `Application`
- **Индекс**: `(hh_negotiation)`, `(application)`

### `ResumeExtract`
Кэш распарсенного резюме — один источник, два возможных происхождения.
- `candidate_profile` — FK → `CandidateProfile`, CASCADE, `related_name='resume_extracts'`
- `source_type` — CharField choices (`ANKETA_FILE`/`HH_RESUME`)
- `source_answer` — FK → `testchecks.Answer`, CASCADE, nullable (для `ANKETA_FILE`)
- `hh_resume_id` — CharField, nullable (для `HH_RESUME` — снепшот id, не FK)
- `raw_text` — TextField
- `structured_data` — JSONField
- `status` — CharField choices (`PENDING`/`DONE`/`FAILED`)
- `error` — TextField, blank
- `provider`, `model`, `prompt_version` — CharField
- `processed_at` — DateTimeField, nullable
- **UniqueConstraint**: `(source_answer)` где `source_answer IS NOT NULL`;
  `(candidate_profile, hh_resume_id)` где `hh_resume_id IS NOT NULL`
- **CheckConstraint**: ровно одно из `source_answer`/`hh_resume_id` заполнено
- Повторный парсинг — новая строка, старая не трогается (иммутабельно после `DONE`);
  при `FAILED` можно перезаписать ту же строку (retry) до первого успеха.
- **PII TTL для неконвертировавшихся HH-лидов** (решение владельца 2026-08-26,
  `02_CONTEXT.md`) — `raw_text`/`structured_data` очищаются фоновой джобой через
  `RESUME_PII_TTL_DAYS` дней для `ResumeExtract`, у которых `candidate_profile` всё ещё
  `application_id IS NULL` (лид не конвертировался в платформенного кандидата). Извлечённые
  факты в `CandidateProfile.facts` не затрагиваются. См.
  `epics/E5-processing-queue/step-E5-06-hh-lead-pii-ttl.md`.

### `AIProcessingJob`
Собственная очередь (раздел 6).
- `candidate_profile` — FK → `CandidateProfile`, CASCADE, **не nullable** (для
  `NEW_HH_LEAD` профиль создаётся синхронно перед постановкой джобы)
- `course` — FK → `courses.Course`, CASCADE, nullable
- `reason` — CharField choices (`NEW_HH_LEAD`/`NEW_APPLICATION`/`NEW_ANSWER`/
  `NEW_RESUME`/`NEW_VIDEO`/`CANDIDATE_DATA_CHANGED`/`VACANCY_PROFILE_CHANGED`/
  `FEEDBACK_APPLIED`/`MANUAL`/`BACKFILL`)
- `status` — CharField choices (`PENDING`/`PROCESSING`/`DONE`/`FAILED`)
- `attempts` — PositiveIntegerField, default 0
- `last_error` — TextField, blank
- `priority` — SmallIntegerField, default 0 (MVP: не используется в сортировке)
- `created_at`, `started_at`, `finished_at`, `retry_after` — DateTimeField, nullable где нужно
- **Индекс**: `(status, retry_after)`
- **Partial UniqueConstraint**: `(candidate_profile, course, reason) WHERE status IN
  ('PENDING', 'PROCESSING')` — защита от дублирующей джобы, если detection на двух
  параллельных тиках (или двух контейнерах при случайном overlap деплоя) увидит одно и
  то же условие независимо, до того как первая джоба успеет его погасить.
  `max_instances=1` (раздел 6) защищает только одну и ту же джобу от повторного входа в
  себя, не от второго процесса/контейнера — этот индекс закрывает именно двойной платный
  AI-вызов на одно и то же событие.
- **on_delete от CandidateProfile**: CASCADE

### `CandidateVacancyAnalysis`
Результат Fit-анализа — иммутабельные версии.
- `candidate_profile` — FK → `CandidateProfile`, CASCADE, `related_name='vacancy_analyses'`
- `course` — FK → `courses.Course`, CASCADE
- `vacancy_profile` — FK → `VacancyProfile`, PROTECT
- `version` — PositiveIntegerField (per `candidate_profile, course`)
- `is_current` — BooleanField, default True
- `fit_score` — SmallIntegerField (0–100), nullable
- `data_completeness` — SmallIntegerField (0–100)
- `confidence` — CharField choices (`LOW`/`MEDIUM`/`HIGH`)
- `recommendation` — CharField choices (`STRONG_MATCH`/`POSSIBLE_MATCH`/`WEAK_MATCH`/
  `NOT_ENOUGH_DATA`/`NOT_A_MATCH`)
- `summary` — TextField
- `strengths`, `risks`, `gaps`, `missing_information`, `criteria_scores`, `evidence`,
  `contradictions`, `interview_questions` — JSONField каждое
- `input_snapshot` — JSONField — копия `CandidateProfile.sources_snapshot` +
  `vacancy_profile_id` + активные `VacancyMemory.id[]` на момент расчёта
- `provider`, `model`, `prompt_version` — CharField
- `tokens_input`, `tokens_output` — IntegerField, nullable
- `cost_estimate` — DecimalField, nullable
- `latency_ms` — IntegerField, nullable
- `analyzed_at` — DateTimeField
- **UniqueConstraint**: `(candidate_profile, course, version)`
- **Индекс**: `(candidate_profile, course, is_current)`
- **on_delete**: CASCADE от `candidate_profile`; PROTECT от `vacancy_profile`
- Versioning: чистое append-only.

### ER-схема (текстовая)

```
CustomUser ──┐
             │ candidate (CASCADE)
             ▼
        Application ──┐                     HHNegotiationRecord
             │ course  │ application(1:1)◄───────┘  application (nullable, SET_NULL)
             ▼         │
          Course ◄─────┘
             │
             │ (VacancyCourseMapping — существующая связь с HH-вакансией)
             │
   ┌─────────┴─────────────────────────────────────┐
   │                                                 │
   ▼ course (CASCADE)                                ▼ course (CASCADE)
VacancyProfile (версии, is_current)          VacancyFeedback ── VacancyMemory
   │                                                 ▲ source_feedback (SET_NULL)
   │ vacancy_profile (PROTECT)
   ▼
CandidateVacancyAnalysis (версии, is_current) ◄── candidate_profile (CASCADE)
   ▲
   │ candidate_profile (CASCADE)
   │
CandidateProfile ──┬── application (1:1, CASCADE, nullable)
   │                └── hh_negotiation (1:1, CASCADE, nullable)
   │
   ├── ResumeExtract[] (candidate_profile CASCADE; source_answer→testchecks.Answer CASCADE, nullable)
   ├── AIProcessingJob[] (candidate_profile CASCADE)
   └── (read-only, внешний источник, без FK из ai_analysis:) TranscriptionJob → testchecks.Answer
```

Ключевое: `ai_analysis` не имеет FK на `CustomUser` напрямую нигде — только
транзитивно через `Application`. Осознанно — упрощает privacy-каскад до одного правила.

## 3. API / контракты

Только проектирование, не реализовывать раньше эпика E8 (`05_EPICS.md`). Неймспейс,
не пересекающийся с существующими сериализаторами кандидата:

```
GET  /api/v1/courses/{course_uuid}/ai-analysis/summary/
     — агрегат для списка: всего/обработано/в очереди/ошибки

GET  /api/v1/courses/{course_uuid}/ai-analysis/candidates/
     — список: candidate_profile_id, fit_score, confidence, data_completeness,
       recommendation, fit_delta (текущий vs предыдущий is_current), demo_progress

GET  /api/v1/courses/{course_uuid}/ai-analysis/candidates/{candidate_profile_id}/
     — полная карточка: текущий CandidateVacancyAnalysis + CandidateProfile.facts
       + evidence + история версий (id, fit_score, analyzed_at, что изменилось)

GET  /api/v1/courses/{course_uuid}/ai-analysis/candidates/{candidate_profile_id}/history/
     — список версий CandidateVacancyAnalysis с input_snapshot diff

GET/POST /api/v1/courses/{course_uuid}/ai-analysis/vacancy-profile/
     — CRUD текущей VacancyProfile (создание = новая версия)

GET/POST /api/v1/courses/{course_uuid}/ai-analysis/feedback/
     — список/создание VacancyFeedback

POST /api/v1/courses/{course_uuid}/ai-analysis/feedback/{id}/approve/
     — approve → создаёт VacancyMemory

POST /api/v1/courses/{course_uuid}/ai-analysis/candidates/{candidate_profile_id}/reanalyze/
     — ручной MANUAL AIProcessingJob
```

Свой сериализатор слой, не трогающий `CourseCandidatesViewSet`/
`CandidateCourseAnswersListView` в `sfera_backend`. Фронтенд ходит к AI-сервису через
BFF-прокси `SPHERA/src/app/api/proxy/` (см. `02_CONTEXT.md`), `sfera_backend` не участвует.

## 4. Слои и файлы

### Candidate Identity — переход HH Lead → Platform Candidate

`CandidateProfile` создаётся при первом касании человека AI-модулем, в одном из двух
состояний, и дозаполняется на месте, никогда не пересоздаётся.

- **Состояние 1 — HH Lead.** Событие `NEW_HH_LEAD` создаёт
  `CandidateProfile(hh_negotiation=<record>, application=None)`.
- **Состояние 2 — Platform Candidate с самого начала** (органика, без HH). Событие
  `NEW_APPLICATION` создаёт `CandidateProfile(application=<application>, hh_negotiation=None)`.
- **Переход.** Когда лид конвертируется, `HHNegotiationRecord.application` становится
  не-null. Detection-джоба на очередном тике видит: есть `HHNegotiationRecord` с
  `application_id IS NOT NULL`, у связанного `CandidateProfile` поле `application` всё
  ещё `None`:
  ```python
  CandidateProfile.objects.filter(hh_negotiation=record, application__isnull=True) \
      .update(application=record.application_id)
  ```
  UPDATE одной строки, не INSERT. Вся история `AIProcessingJob`/
  `CandidateVacancyAnalysis`/`ResumeExtract` остаётся привязанной к той же
  `candidate_profile_id`. Гонки — см. `02_CONTEXT.md`.

### Candidate Identity — Merge кандидатов (`Application.merged_into`)

Платформа умеет дедуплицировать кандидатов вручную — `Application.merged_into`
(self-FK, `SET_NULL`) плюс аудит-лог `CandidateMergeLog`
(`PLATFORM_AUDIT_REFERENCE.md`, раздел 2). AI-модуль об этом не узнаёт сам по себе —
явно детектируется отдельным шагом detection-джобы, тем же способом, каким уже
детектируются новые `Answer` (раздел 5, «Change Detection») — по монотонному `id`
`CandidateMergeLog` с прошлого тика:

Названия полей `CandidateMergeLog` ниже проверены против реального кода
`sfera_backend/sfera_backend/courses/models.py` (`CandidateMergeLog`, там же —
`duplicate_application`/`canonical_application`, не `source`/`target`) — при реализации
E5-шага **не копировать это как есть**, а заново снять список колонок живой
reflection'ом (`reflect_platform_tables(..., tables=["courses_candidatemergelog"])`) —
та же защита, что уже даёт unit-тест E0-03, применить и здесь.

```python
new_merges = CandidateMergeLog.objects.filter(id__gt=last_seen_merge_log_id)
for log in new_merges:
    source_profile = CandidateProfile.objects.filter(application_id=log.duplicate_application_id).first()
    if source_profile is None or source_profile.is_superseded:
        continue
    target_profile = CandidateProfile.objects.filter(application_id=log.canonical_application_id).first()
    if target_profile is None:
        # у выжившего Application своего профиля ещё нет — просто переносим FK,
        # история (facts/AIProcessingJob/CandidateVacancyAnalysis) едет вместе
        source_profile.application_id = log.target_application_id
        source_profile.save(update_fields=["application"])
    else:
        # у обоих Application уже есть своя AI-история — не сливаем автоматически
        # (риск молча перезаписать чужую историю), профиль-источник помечается
        # superseded и перестаёт участвовать в живой обработке
        source_profile.is_superseded = True
        source_profile.superseded_by = target_profile
        source_profile.save(update_fields=["is_superseded", "superseded_by"])
```

`is_superseded=True` исключает профиль из очереди detection/processing (фильтр
`is_superseded=False` во всех выборках `CandidateProfile` для джоб). Живая работа для
такого кандидата продолжается через `target_profile`; история `source_profile`
остаётся в БД как архив, не удаляется и не переносится автоматически — ручное слияние
двух AI-историй (facts из обоих профилей) вне scope MVP, решение владельца от
2026-08-26 (см. `02_CONTEXT.md`).

### Candidate Profile — как строится и обновляется

`facts` — плоский список типизированных фактов с evidence. Источники подмешиваются
независимо и опционально:

| Источник | Что даёт | Может отсутствовать |
|---|---|---|
| HH resume (`ResumeExtract`, `HH_RESUME`) | опыт, должности, компании, зарплатные ожидания | да |
| Анкетное резюме (`ResumeExtract`, `ANKETA_FILE`) | то же + написанное кандидатом | да |
| Ответы (`Answer.text`) | прямые факты из анкеты | да, частично |
| Видео (внешний `TranscriptionJob.transcript_text`+`summary_text`) | мотивация, речь | да |

`data_completeness` — «сколько из 4 источников реально присутствует и обработано», без
привязки к содержанию — специально отделено от `fit_score`, который живёт только в
`CandidateVacancyAnalysis` (profile никогда не пишет число «подходит на N%»).

Обновление — не полная пересборка каждый раз: сервис читает `sources_snapshot`,
сравнивает с текущим состоянием источников (раздел 5), дополняет `facts` только тем,
что реально новое, инкрементирует `version`, пишет новый `sources_snapshot`.

### Vacancy Profile + Vacancy Memory workflow

Заполняется вручную менеджером (UI — не в этом этапе). Версии иммутабельны, `is_current`
— один флаг на `course`.

1. Менеджер пишет `VacancyFeedback.text`.
2. AI формирует `ai_suggested_rule` (отдельный дешёвый LLM-вызов, синхронный или через
   `AIProcessingJob` с `reason=FEEDBACK_APPLIED`).
3. Менеджер утверждает (UI-кнопка, вне этого этапа) → создаётся
   `VacancyMemory(rule_text=..., source_feedback=feedback, approved_by=..., is_active=True)`,
   `feedback.applied=True`.
4. `VacancyMemory` не переписывает `VacancyProfile.requirements` автоматически — оба
   подмешиваются в prompt Fit-скоринга как отдельные блоки контекста.
5. Появление активной `VacancyMemory` или новой `is_current=True` версии `VacancyProfile`
   → `AIProcessingJob(reason=VACANCY_PROFILE_CHANGED)` для всех
   `CandidateVacancyAnalysis.is_current=True` этого `course` — только пересчёт Fit.

Positive feedback — та же модель `VacancyFeedback`, `sentiment=POSITIVE`, тот же путь
до `VacancyMemory` с `weight_hint=BOOST`.

### Resume Pipeline

```
Источник (Answer.file ANKETA_RESUME | HHNegotiationRecord.hh_resume_id)
        │
        ▼  проверка: ResumeExtract с этим source_answer / (candidate_profile, hh_resume_id) уже DONE?
   да ──┴── нет
   │         ▼
   │    создать ResumeExtract(status=PENDING)
   │         ▼
   │    скачать файл (Django storage API) ИЛИ HH API get_resume_pdf (той же функцией,
   │    что и существующий эндпоинт — не писать новый клиент)
   │         ▼
   │    extract text (PDF/DOC parser — библиотека вне этого этапа)
   │         ▼
   │    LLM → structured_data
   │         ▼
   │    status=DONE, processed_at=now
   ▼
переиспользовать raw_text/structured_data → добавить факты в CandidateProfile.facts
```

Кэш означает: HH API дёргается ровно один раз на `hh_resume_id` (риск rate-limit
закрыт). Анкетный файл — ровно один раз на `Answer.id` (гарантировано
`UniqueConstraint` на `ResumeExtract.source_answer` + иммутабельность `Answer`).

### Video Pipeline

Не строится заново. AI-модуль — потребитель уже согласованного плана
`PLATFORM_video-transcription-plan/`. Рекомендация: реализовать `TranscriptionJob`-часть
до или параллельно с AI-модулем, как отдельный технический слой (другой профиль
нагрузки: CPU-bound, свой воркер, свой `SELECT FOR UPDATE SKIP LOCKED`, тогда как
AI-Fit-скоринг I/O-bound через OpenRouter).

Интеграция: сервис сборки `CandidateProfile` делает
`TranscriptionJob.objects.filter(answer_id=video_answer_id, status='DONE').first()`
(кросс-приложение read, без дублирования). Если ещё не готов — факты о видео просто
отсутствуют (`data_completeness` ниже), детекция подхватит на следующем тике, когда
транскрипт появится (`NEW_VIDEO` = «появился готовый `TranscriptionJob.DONE`», не
«появился `Answer`»).

Жёсткое ограничение: `clean_expired_videos()` удаляет видеофайл через 30 дней — но
`transcript_text` к этому моменту уже сохранён. AI-модуль полагается только на текст,
не на сам видеофайл.

### Answers Pipeline

Detection: `MAX(Answer.id)` (не `answered_at` — `id` монотонен, не подвержен часовым
поясам/дублям) на дату последнего анализа, сохранённый в
`CandidateProfile.sources_snapshot['max_answer_id']`. На каждом тике —
`Answer.objects.filter(attempt__candidate=..., id__gt=snapshot['max_answer_id'])`.
Поскольку `Answer` неперезаписываем, это надёжно закрывает и «появились новые», и
«старые не могли измениться».

Резюме-Answer и видео-Answer обрабатываются отдельными под-пайплайнами при первом
появлении; остальные текстовые/выбор-ответы идут прямо в `facts` через LLM-вызов по
батчу новых `Answer` (не по одному — экономия токенов/вызовов).

## 5. Change Detection — точный алгоритм

Псевдокод ниже на SQLAlchemy (не Django ORM — сервис не использует Django-style
менеджеры `.objects`/relationship-обходы, см. раздел 1). `profile.application_id` /
`profile.hh_negotiation_id` — простые Integer-колонки без FK; платформенные таблицы
читаются через reflected `platform_base.classes.*` явными `select()`-запросами.

**Scope reflection'а.** `MetaData.reflect(only=[...])` по умолчанию (`resolve_fks=True`)
тянет за собой и таблицы, на которые ссылается FK у явно перечисленных — например,
`testchecks_answer.attempt_id → testchecks_testattempt` не входит в список, но
подтянется всё равно. Это тихо расширяет заявленный «читаем только N таблиц» scope и
может упереться в отсутствие `GRANT SELECT` у read-only роли для неожиданно подтянутой
таблицы. При росте числа читаемых таблиц (E2+, `headhunter_hhnegotiationrecord`,
`courses_course`, `courses_progress`) — либо передавать `resolve_fks=False` явно, либо
держать список `GRANT SELECT` синхронным с фактическим transitively-pulled-in набором
(см. также `step-E0-03-reflection-module.md`).

```python
from sqlalchemy import func, select

def needs_profile_rebuild(session, profile) -> bool:
    snap = profile.sources_snapshot
    application = (
        session.get(platform_base.classes.courses_application, profile.application_id)
        if profile.application_id else None
    )
    progress_updated_at = None
    max_answer_id = None
    if application is not None:
        progress_updated_at = session.scalar(
            select(platform_base.classes.courses_progress.updated_at)
            .where(
                platform_base.classes.courses_progress.candidate_id == application.candidate_id,
                platform_base.classes.courses_progress.course_id == application.course_id,
            )
        )
        max_answer_id = session.scalar(
            select(func.max(platform_base.classes.testchecks_answer.id))
            .join(platform_base.classes.testchecks_testattempt)
            .where(platform_base.classes.testchecks_testattempt.candidate_id == application.candidate_id)
        )
    hh_negotiation = (
        session.get(platform_base.classes.headhunter_negotiation, profile.hh_negotiation_id)
        if profile.hh_negotiation_id else None
    )
    current = {
        'application_updated_at': application.updated_at if application else None,
        'progress_updated_at': progress_updated_at,
        'max_answer_id': max_answer_id,
        'hh_negotiation_updated_at': hh_negotiation.updated_at if hh_negotiation else None,
        'hh_resume_id': hh_negotiation.hh_resume_id if hh_negotiation else None,
    }
    return current != snap  # любое несовпадение полей → профиль устарел

def needs_fit_recalc(session, profile, course_id) -> bool:
    current_analysis = session.scalar(
        select(CandidateVacancyAnalysis).where(
            CandidateVacancyAnalysis.candidate_profile_id == profile.id,
            CandidateVacancyAnalysis.course_id == course_id,
            CandidateVacancyAnalysis.is_current.is_(True),
        )
    )
    if current_analysis is None:
        return True
    current_vp = session.scalar(
        select(VacancyProfile).where(VacancyProfile.course_id == course_id, VacancyProfile.is_current.is_(True))
    )
    active_memory_ids = set(
        session.scalars(
            select(VacancyMemory.id).where(VacancyMemory.course_id == course_id, VacancyMemory.is_active.is_(True))
        )
    )
    stale_profile = profile.version != current_analysis.input_snapshot.get('candidate_profile_version')
    stale_vacancy = current_vp and current_vp.id != current_analysis.input_snapshot.get('vacancy_profile_id')
    stale_memory = active_memory_ids != set(current_analysis.input_snapshot.get('memory_ids', []))
    return stale_profile or stale_vacancy or stale_memory
```

Три независимых уровня детекции:
1. **Профиль устарел** → пересобрать `CandidateProfile`, затем пересчитать все
   `CandidateVacancyAnalysis` этого кандидата (по всем вакансиям, где он есть).
2. **Только вакансия изменилась** → не трогать `CandidateProfile`, пересчитать только
   `CandidateVacancyAnalysis` этой пары.
3. **Ничего не изменилось** → ни одного AI-вызова, джоба не создаётся вообще
   (detection-функция сама по себе не расходует бюджет — чистый SQL-запрос).

## 6. Processing Queue

`AIProcessingJob` — модель из раздела 2. Обработка — свой процесс внутри контейнера
AI-сервиса, не `core/scheduler.py` (чужой Django-процесс, не трогать). Тик (detection +
постановка джоб + обработка очереди) — не непрерывный `interval`, а фиксированное
расписание 3 раза в день, чтобы AI-вызовы (Fit/резюме/фидбек) не размазывались по всему
дню, а шли предсказуемыми пачками:

```python
# ai_service/scheduler.py — свой BackgroundScheduler, свой процесс, свой контейнер
from apscheduler.triggers.cron import CronTrigger

def process_ai_jobs():
    from ai_service.job_processing import process_batch
    process_batch(limit=AI_ANALYSIS_MAX_CONCURRENT_JOBS)

scheduler = BackgroundScheduler(timezone=SETTINGS.timezone)  # тот же TZ, что у backend'а
scheduler.add_job(
    process_ai_jobs,
    CronTrigger(hour='8,15,19', minute=0),
    max_instances=1,  # тик не параллелится сам с собой — только джобы внутри тика
)
scheduler.start()
```

Detection (постановка джоб, раздел 5) и обработка очереди — часть одного и того же тика:
на каждом запуске сперва детектируются изменившиеся кандидаты/вакансии и создаются
`PENDING`-джобы, затем тот же вызов разбирает очередь `process_batch`. Между тиками джобы
просто ждут в БД — это безопасно (см. «Идемпотентность» ниже, переживает рестарт
контейнера).

`process_batch` — блокировка N `PENDING`-джобов через SQLAlchemy, не Django-style:
```python
jobs = session.scalars(
    select(AIProcessingJob)
    .where(AIProcessingJob.status == "PENDING")
    .order_by(AIProcessingJob.created_at)
    .limit(batch_size)
    .with_for_update(skip_locked=True)
).all()
```
(параллелить в `ThreadPoolExecutor` внутри одного тика — задачи независимые и I/O-bound
через OpenRouter). Каждая джоба — свой try/except, падение одной не блокирует остальные
(`FAILED`, `last_error`, `attempts += 1`, `retry_after = now + backoff(attempts)`).

**Идемпотентность**: джоба на входе заново вызывает `needs_profile_rebuild`/
`needs_fit_recalc` — если условие уже перестало быть истинным, помечается `DONE` без
AI-вызова. Повторный запуск после падения контейнера безопасен по той же причине.

**Зависшие `PROCESSING`** — отдельный cron (раз в час) переводит `PROCESSING`-джобы
старше N часов обратно в `PENDING` (не в `FAILED`) с инкрементом `attempts`.

## AI Pipeline — какие вызовы и когда

| Этап | Вызов | Когда |
|---|---|---|
| Resume parsing | LLM (text→structured) | 1 раз на `Answer`/`hh_resume_id`, при `NEW_RESUME` |
| Video facts | нет отдельного вызова — читает готовый `TranscriptionJob.summary_text` | при `NEW_VIDEO` |
| Answers → facts | LLM (батч новых `Answer.text`) | при `NEW_ANSWER`, батчем |
| Fit scoring | LLM (`facts` + `requirements` + активные `VacancyMemory` → скор+evidence+recommendation) | при пересборке профиля ИЛИ изменении вакансии |
| Feedback interpretation | LLM (`VacancyFeedback.text` → `ai_suggested_rule`) | при создании `VacancyFeedback` |

Все вызовы — через единый тонкий клиент `ai_analysis/providers.py` (OpenRouter +
отдельный STT-provider уже есть в чужом плане) с сохранением
`provider`/`model`/`prompt_version`/токенов/latency на каждой строке-результате — не
универсальная AI-платформа, просто обёртка с логированием стоимости.

## Versioning — сводно

- **`VacancyProfile`**: иммутабельные версии, один `is_current`.
- **`CandidateProfile`**: одна мутируемая строка, `version` — счётчик, `sources_snapshot`
  — что учтено. Полной истории снепшотов профиля не храним.
- **`CandidateVacancyAnalysis`**: иммутабельные версии на пару `(candidate_profile,
  course)`, `is_current` — ровно одна на пару. `input_snapshot` внутри каждой версии
  объясняет, почему скор изменился (`52→87` объясняется диффом `input_snapshot` между
  версиями).

## 7. Риски и решения (mini-ADR)

### Schema drift (заметка, найдено при архитектурном ревью, 2026-08-26)

Reflection полностью runtime — AI-сервис не видит миграций `sfera_backend` заранее,
только когда они уже накатились. Переименование/удаление колонки, которую сервис читает,
проявится как рантайм-ошибка (или, хуже, тихо как `NULL`, если колонку переименовали, а
не удалили), а не как ошибка деплоя. Это осознанный trade-off (read-only reflection —
чтобы не создавать зависимость от чужой схемы), не баг сам по себе. Рассмотреть на
E2/E5: лёгкая startup- или scheduled-проверка, которая reflect'ит список колонок, от
которых сервис реально зависит, и алертит (не просто падает молча), если чего-то не
хватает.

### Cost Protection

1. Change detection — чистый SQL, без AI-вызовов, перед постановкой любой джобы.
2. `ResumeExtract`/`TranscriptionJob` кэш — файл/резюме обрабатывается максимум 1 раз.
3. `AIProcessingJob` идемпотентен — повторная проверка условия перед реальным вызовом.
4. Раздельные уровни детекции (профиль vs вакансия) — не пересчитывается то, что не
   могло измениться.
5. Батчинг новых `Answer` вместо вызова на каждый ответ.
6. `tokens_input/output`/`cost_estimate` на каждой строке — наблюдаемость затрат (не
   автоматический лимит на этом этапе — открытый вопрос №3, `02_CONTEXT.md`).
7. Partial UniqueConstraint на `AIProcessingJob` (раздел 2) — защита от двойной
   постановки одной и той же джобы при параллельном detection (два контейнера/overlap
   тиков), дополняет п.3 (идемпотентность внутри одной джобы) на уровне создания, а не
   только обработки.

### Failure Scenarios

| Сценарий | Поведение |
|---|---|
| OpenRouter недоступен | `AIProcessingJob.FAILED`, `last_error`, `retry_after` с backoff; `CandidateVacancyAnalysis` не создаётся (предыдущая `is_current` версия остаётся видимой) |
| STT (внешний пайплайн) недоступен | вне ответственности AI-модуля — видео-факты отсутствуют, `data_completeness` ниже, `NEW_VIDEO` не триггерится, пока `TranscriptionJob` не `DONE` |
| HH API недоступен | `ResumeExtract.FAILED`, retry на следующем тике; `CandidateProfile` собирается без HH-резюме (partial), не блокирует остальные факты |
| Битый resume (не парсится) | `ResumeExtract.FAILED` с `error`, `CandidateProfile` собирается без этого источника; ручной `MANUAL` retry после фикса |
| Битое video | вне ответственности AI-модуля (см. STT выше) |
| Scheduler перезапустился | `PENDING`/зависшие `PROCESSING` джобы переживают рестарт (БД-очередь, не in-memory); зависшие переводятся обратно в `PENDING` по таймауту |
| Job завис | cron-детектор зависших `PROCESSING` (раздел 6) |
| AI вернул невалидный JSON | try/except вокруг парсинга ответа LLM → `FAILED` с сырым ответом в `last_error` (обрезанным), не пишется частичный `CandidateVacancyAnalysis` |
| Один кандидат упал при обработке партии | `process_batch` — try/except на джобу, остальные продолжают |
| Кандидат удалён во время обработки | см. `02_CONTEXT.md`, «Граничные случаи» |
| Vacancy Profile изменился во время processing | см. `02_CONTEXT.md`, «Граничные случаи» |

### Migration Plan (не создавать сейчас)

Инструмент — Alembic (стандарт для SQLAlchemy, не Django migrations). Каждая ревизия —
против той же Postgres, что использует `sfera_backend`, но в своих таблицах (`ai_`-префикс,
чтобы визуально не путать с `courses_`/`testchecks_`).

1. `0001_initial` — `ai_vacancy_profile`, `ai_candidate_profile`, `ai_resume_extract`
   (FK на `courses_course`/`courses_application`/`headhunter_hhnegotiationrecord`/
   `testchecks_answer` — `ondelete='CASCADE'` явно в DDL)
2. `0002` — `ai_processing_job`
3. `0003` — `ai_candidate_vacancy_analysis`
4. `0004` — `ai_vacancy_feedback`, `ai_vacancy_memory`

Разбивка на 4 ревизии — чтобы каждый эпик (`05_EPICS.md`) был отдельно тестируем и
деплоим независимо. Исполняется вручную/через deploy-скрипт AI-сервиса — не имеет
отношения к `python manage.py migrate` backend'а.

### Инфраструктура и сеть

Проверено по `sfera_backend/docker-compose.staging.yml`: `db` не публикует порт наружу,
`backend`/`scheduler` ходят в неё только по внутренней docker-сети того же
compose-проекта. Порт наружу торчит только у `gateway` (8081).

Чтобы AI-сервис (отдельный репозиторий, отдельный `docker-compose`) мог подключиться к
тому же `db`, не открывая Postgres в интернет:

1. **Тот же VPS, общая docker-сеть (выбрано).** В `docker-compose.staging.yml`
   объявить `db` в именованной внешней сети (`networks: { ai_shared: { external: true } }`),
   AI-сервис в своём compose подключается к той же внешней сети по имени. `db`
   резолвится по DNS-имени контейнера, порт остаётся недоступен снаружи VPS.
   Требует правки `docker-compose.staging.yml` backend'а (объявление сети) —
   владелец дал добро 2026-08-25 (`02_CONTEXT.md`).
2. Альтернатива, не выбрана: `db` на `127.0.0.1:5432`, AI-контейнер через
   `host.docker.internal`/`--network=host` — более узкая правка, но завязана на
   localhost-специфику Docker.

В обоих случаях: отдельный **read-only Postgres-пользователь** для reflection-чтения
платформенных таблиц (`GRANT SELECT ON ...`, без прав на запись) — AI-сервис физически
не сможет случайно испортить данные backend'а даже при баге в коде. Роль для своих 7
таблиц — отдельная, с полными правами только на них.

**Известная нестабильность (повторяется):** контейнеры `db`/`backend` периодически
отваливаются от сети `ai_shared` — вероятно, при пересборке/рестарте staging-стека
(`docker-compose up` без явного переподключения внешней сети). Обнаружено минимум дважды:
`backend` — до 2026-09-01, `db` и `backend` одновременно — 2026-09-01 (оба переподключены
вручную: `docker network connect ai_shared <container>`). Перед любым тоннелированием
(`scripts/tunnel-platform-db.sh` и планируемый `scripts/tunnel-backend.sh`, E11-01) стоит
сначала проверить `docker network inspect ai_shared`, а не сразу считать проблему в коде
AI-сервиса.

## 8. Что НЕ ломаем

- Не менять `sfera_backend`/`SPHERA` без отдельного явного разрешения на каждую
  конкретную правку (единственное согласованное исключение —
  `docker-compose.staging.yml`, общая docker-сеть).
- Не писать в таблицы `courses_*`/`testchecks_*`/`users_*`/`headhunter_*` — доступ к БД
  платформы только read-only.
- Не трогать `core/scheduler.py` (чужой Django-процесс) — свой APScheduler в своём
  контейнере.
- Не дублировать HTTP-клиент к HH API логикой из backend — переиспользовать контракт
  `get_resume_pdf`, но собственной реализацией (разные репозитории, чужой код
  недоступен для импорта).
- Не сливать транскрибацию видео в этот сервис — читает `TranscriptionJob` как внешний
  источник (см. `02_CONTEXT.md`, пункт 2 «Отклонения от ТЗ»).

## Future Export (за рамками MVP)

Данные уже структурированы для `Карточка_Резюме.pdf + ВидеоВизитка.mp4` без переделки
моделей:
- «AI-карточка» PDF — рендерится из `CandidateVacancyAnalysis.is_current`
  (summary/strengths/risks) + `CandidateProfile.facts`.
- «оригинальное резюме» — тот же `Answer.file`/HH PDF, что уже переиспользуется в
  `collect_candidate_archive_entries` — export-сервис берёт готовую функцию, не пишет
  новую.
- «видеовизитка» — тот же `Answer.file` (video S3 key), тоже уже есть готовая сборка в
  архивном сервисе.
Может быть построен как новый сервисный модуль в `ai_analysis/`, переиспользующий
`collect_candidate_archive_entries`-подобную логику + `CandidateVacancyAnalysis` для
PDF-контента — без миграций сверх раздела 2.
