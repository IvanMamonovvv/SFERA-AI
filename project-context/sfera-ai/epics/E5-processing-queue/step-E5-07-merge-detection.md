# Шаг E5-07 — детекция platform-merge (`CandidateMergeLog`)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E2 (`CandidateProfile.is_superseded`/`superseded_by`)
**Перед началом:** прочитай `03_TDD.md` раздел «Candidate Identity — Merge кандидатов
(`Application.merged_into`)».

## Цель

Ручное слияние кандидатов на платформе (`CandidateMergeLog`) отражается в
`CandidateProfile` — старый профиль либо переезжает на нового `application_id`, либо
помечается `is_superseded`, без ручного вмешательства.

## Контекст (проверено 2026-08-27 живой reflection'ом на staging)

`courses_candidatemergelog` — реальные колонки (НЕ `source`/`target`, как ошибочно было
в `PLATFORM_AUDIT_REFERENCE.md`):

```
id                          BIGINT
created_at                  TIMESTAMP
modified_at                 TIMESTAMP
snapshot                    JSONB
canonical_application_id    BIGINT   -- выживший Application
duplicate_application_id    BIGINT   -- поглощённый Application
performed_by_id             BIGINT, nullable
```

Курсор `last_seen_merge_log_id` — глобальный (не привязан к профилю, в отличие от
`max_answer_id` в `sources_snapshot`). Хранить в новой key-value таблице собственной
схемы `ai_service_state` (`key` PK, `value` TEXT, `updated_at`) — простейший вариант,
достаточный для одного курсора; не привязываться к более сложной схеме ради одного поля.

## Что сделать

1. Модель `AiServiceState` (`ai_service_state`): `key` (String, PK), `value` (Text,
   nullable), `updated_at` (TimestampMixin). Alembic-ревизия.
2. `MERGE_DETECTION_TABLES = ("courses_candidatemergelog",)` в `platform_db.py`.
3. `detect_and_process_merges(session, platform_base)` в новом
   `src/sfera_ai/services/merge_detection.py`:
   - читает `last_seen_merge_log_id` из `ai_service_state` (0, если ключа нет)
   - выбирает `CandidateMergeLog` с `id > last_seen_merge_log_id`, по возрастанию `id`
   - на каждую запись — алгоритм из TDD:
     - `source_profile` = `CandidateProfile` по `application_id == duplicate_application_id`;
       если нет или уже `is_superseded` — пропустить
     - `target_profile` = `CandidateProfile` по `application_id == canonical_application_id`
     - если `target_profile is None` — `source_profile.application_id = canonical_application_id`
     - иначе — `source_profile.is_superseded = True`,
       `source_profile.superseded_by_id = target_profile.id`
   - обновляет `last_seen_merge_log_id` на максимальный обработанный `id` (курсор
     двигается даже если ни один лог не привёл к реальному изменению профиля —
     иначе один и тот же уже отсмотренный merge будет пересматриваться каждый тик)
4. Не создаёт `AIProcessingJob` — TDD не требует отдельной джобы на сам merge, только
   корректность `is_superseded`/`application_id`.
5. Убедиться, что все существующие выборки `CandidateProfile` для detection/processing
   (E5-02/E5-03/E5-04) уже фильтруют `is_superseded=False`, либо добавить фильтр там,
   где отсутствует — сверить по факту, не полагаться на память из TDD.

## Файлы

- `src/sfera_ai/models/ai_service_state.py`
- `migrations/versions/0006_ai_service_state.py`
- `src/sfera_ai/services/merge_detection.py`
- `src/sfera_ai/platform_db.py` — `MERGE_DETECTION_TABLES`
- `tests/models/test_ai_service_state.py`
- `tests/services/test_merge_detection.py`

## Критерии готовности (DoD)

- [x] Перенос FK (target ещё без своего профиля) — тест
- [x] Пометка `is_superseded`+`superseded_by` (у target уже есть профиль) — тест
- [x] Повторный тик без новых merge-логов не трогает уже обработанные профили — тест
- [x] Курсор двигается даже когда `source_profile` не найден/уже `is_superseded` — тест
- [x] `uv run pytest` без регрессий
- [x] Alembic upgrade/downgrade чисто (upgrade head — на staging через туннель;
      downgrade — только на отдельной SQLite, не на staging)

## Как проверить

```bash
uv run pytest tests/models/test_ai_service_state.py tests/services/test_merge_detection.py -v
uv run alembic upgrade head
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — реализовано: модель `AiServiceState` (key-value курсор,
  `src/sfera_ai/models/ai_service_state.py`), ревизия `0006`
  (`migrations/versions/0006_ai_service_state.py`), `MERGE_DETECTION_TABLES` в
  `platform_db.py`, `detect_and_process_merges` в `src/sfera_ai/services/merge_detection.py`.
  `courses_candidatemergelog` проверен живой reflection'ом на staging перед реализацией —
  `PLATFORM_AUDIT_REFERENCE.md` не описывал точные имена колонок, TDD предупреждал не
  копировать пример как есть; реальные колонки совпали с псевдокодом TDD
  (`canonical_application_id`/`duplicate_application_id`, не `source`/`target`).
  Побочно найден и исправлен пробел DoD-пункта 5: `detect_and_enqueue`
  (`job_detection.py`, выборка `existing_profiles` для `CANDIDATE_DATA_CHANGED`) не
  фильтровала `is_superseded=False` — добавлен фильтр, иначе после появления этого шага
  superseded-профили продолжили бы попадать в детекцию. Тесты —
  `tests/models/test_ai_service_state.py` (2), `tests/services/test_merge_detection.py`
  (5: перенос FK, пометка superseded, курсор двигается без совпавшего source, повторный
  тик без новых логов не трогает уже обработанное, уже-superseded источник пропускается).
  Не создаёт `AIProcessingJob` на сам merge — TDD этого не требует. Upgrade head применён
  на staging через туннель (FK на платформу нет, GRANT не понадобился);
  upgrade+downgrade полного цикла проверен на отдельной SQLite-БД. Полный сьют
  `uv run pytest` — 101 passed, регрессий нет.
