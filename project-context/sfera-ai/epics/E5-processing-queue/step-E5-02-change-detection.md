# Шаг E5-02 — Change Detection (`needs_profile_rebuild`, `needs_fit_recalc`)

**Статус:** PARTIAL — `needs_profile_rebuild` DONE, `needs_fit_recalc` отложен (см. журнал)
**Слой:** Backend · **Зависит от:** E5-01
**Перед началом:** прочитай `03_TDD.md` раздел «5. Change Detection — точный алгоритм»
(готовый псевдокод), раздел «7. Риски» → Cost Protection.

## Цель

Обе функции детекции реализованы 1:1 по алгоритму TDD, покрыты тестами на все три
уровня («профиль устарел» / «только вакансия» / «ничего»), не делают ни одного
AI-вызова.

## Что сделать

1. `needs_profile_rebuild(profile) -> bool` — сравнение `sources_snapshot` с текущим
   состоянием источников (Application/Progress/max Answer id/HH negotiation/hh_resume_id).
2. `needs_fit_recalc(profile, course) -> bool` — сравнение `input_snapshot` последнего
   `is_current` анализа с текущей версией `VacancyProfile`/активными `VacancyMemory`.
3. Чистый SQL/ORM-запросы, без побочных эффектов, без сети.

## Файлы

- `src/sfera_ai/services/change_detection.py`
- `tests/services/test_change_detection.py` — три сценария на каждую функцию
  (устарело/не устарело/граница)

## Критерии готовности (DoD)

- [ ] Все три уровня детекции покрыты тестами
- [ ] Ни один тест не мокает AI-вызов (потому что вызовов нет)

## Как проверить

```bash
uv run pytest tests/services/test_change_detection.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — **найден и исправлен баг на реальном прогоне на staging** (в рамках
  проверки E5-06 весь эпик E5 гонялся вживую): `needs_profile_rebuild` читал
  `.updated_at` у `Application`/`Progress`/`HHNegotiationRecord`, но платформа —
  Django-модели, реальная колонка называется `modified_at` (`updated_at` нигде не
  существует). Юнит-тесты этого не ловили — самодельная SQLite-схема в
  `_platform_base()` называла колонку `updated_at`, повторяя ошибку кода, а не
  реальную схему платформы. Упало на первом же реальном тике (`AttributeError:
  'headhunter_hhnegotiationrecord' object has no attribute 'updated_at'`).
  Исправлено: `.modified_at` в `change_detection.py`, тестовые фикстуры
  `test_change_detection.py`/`test_job_detection.py` тоже переведены на `modified_at`
  (ключи `sources_snapshot`-словаря — `application_updated_at` и т.п. — не трогал, это
  внутренние лейблы кода, не имена колонок). Полный сьют `uv run pytest` — 82 passed
  после фикса. Вывод: самодельные SQLite-фикстуры реальную схему платформы не
  гарантируют — расхождение нашлось только на реальной БД.
- `2026-08-27` — `needs_profile_rebuild(platform_base, profile)` реализован в
  `src/sfera_ai/services/change_detection.py` — сравнение `sources_snapshot` с текущим
  состоянием `courses_application`/`courses_progress`/`testchecks_answer`+`testchecks_testattempt`/
  `headhunter_hhnegotiationrecord` через reflection (константа `CHANGE_DETECTION_TABLES` в
  `platform_db.py`). Datetime-поля сериализуются в `isoformat()`-строки для сравнения с JSON-снепшотом.
  Тесты `tests/services/test_change_detection.py` — 3 сценария (устарело/не устарело/граница
  — профиль только с `hh_negotiation_id`, без `application_id`). Полный сьют 66 passed.

  **`needs_fit_recalc` отложен.** По TDD-псевдокоду (`03_TDD.md` раздел 5) она читает
  `CandidateVacancyAnalysis` и `VacancyMemory` — этих моделей нет в коде: они относятся к
  ещё не начатым эпикам E6 (`step-E6-02-analysis-model.md`) и E7 (`step-E7-01-models.md`).
  Проверено по всему `epics/` — это единственный такой разрыв в графе (E8/E9 зависят от
  E6+E7 напрямую, там гэпа не будет). Решение владельца (2026-08-27): не создавать эти
  модели заранее вне их эпиков — реализовать `needs_fit_recalc` отдельным шагом, когда
  дойдём до E6/E7. Остальной шаг (job-creation E5-03 и далее) `needs_fit_recalc` не
  использует — не блокирует.
