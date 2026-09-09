# Шаг E14-10 — Change detection должен замечать готовый транскрипт видео

**Статус:** DONE (код+тесты). Staging-проверка на реальном TranscriptionJob(DONE) — отдельно, после
деплоя E14-01/02/03.
**Слой:** Backend · **Зависит от:** E14-01, E14-02, E14-03 (нужен реальный `TranscriptionJob`
со статусом `DONE`, чтобы проверить фикс на живых данных)
**Репозиторий:** `SFERA-AI` (этот репозиторий, не `sfera_backend`) — правка в уже сданном коде
эпика E5, разрешения на чужой репозиторий не требует.
**Перед началом:** прочитай `src/sfera_ai/services/change_detection.py` (текущая реализация
`compute_current_sources_snapshot`), `03_TDD.md` раздел «5. Change Detection» и раздел
«Video Pipeline», `src/sfera_ai/platform_db.py` (`VIDEO_FACTS_TABLES`).

## Цель

Завершение `TranscriptionJob` (`PENDING → DONE`) кандидата помечает его профиль как требующий
пересборки — так же, как сейчас это делают новый ответ или новое резюме.

## Проблема (найдено ревью архитектора, 2026-09-07)

`compute_current_sources_snapshot()` сравнивает 5 полей: `application_updated_at`,
`progress_updated_at`, `max_answer_id`, `hh_negotiation_updated_at`, `hh_resume_id`. Видео-`Answer`
создаётся один раз в момент записи видеовизитки — задолго до того, как транскрипт станет `DONE`
(транскрибация асинхронна, идёт в фоне отдельным воркером). Готовность транскрипта не меняет ни
одно из 5 полей снапшота → `needs_profile_rebuild` не сработает → `_video_facts`
(`candidate_facts.py:86`) никогда не попадёт в `CandidateProfile.facts`/`fit_score`, если только
профиль случайно не пересоберётся по другой причине уже после готовности транскрипта. Без этого
шага весь смысл эпика E14 для AI-скоринга кандидата теряется — транскрипт будет виден HR в карточке
(E14-05/06), но не будет влиять на оценку.

## Что сделать

1. В `compute_current_sources_snapshot()` добавить 6-е поле снапшота — состояние видео-транскрипции
   кандидата. Вариант: `MAX(TranscriptionJob.finished_at)` (или конкатенация `status` по всем
   видео-`Answer` кандидата) через join `testchecks_transcriptionjob` → `testchecks_answer` →
   `testchecks_testattempt` по `candidate_id` (тот же паттерн join, что уже есть для `max_answer_id`
   на строках 40-44).
2. Проверить на реальных данных staging (после E14-01/02/03 задеплоены и хотя бы один
   `TranscriptionJob` реально дошёл до `DONE`): `needs_profile_rebuild` должен вернуть `True` сразу
   после перехода джобы в `DONE`, не дожидаясь совпадения с другой причиной пересборки.
3. Обновить юнит-тесты `compute_current_sources_snapshot`/`needs_profile_rebuild` — добавить кейс
   «транскрипт стал DONE → снапшот изменился → rebuild нужен».

## Файлы

- `src/sfera_ai/services/change_detection.py` — добавить поле в снапшот
- `tests/services/test_change_detection.py` (или аналог) — новый кейс
- `src/sfera_ai/platform_db.py` — `VIDEO_FACTS_TABLES`/`CANDIDATE_FACTS_TABLES` уже содержат
  `testchecks_transcriptionjob`, менять не нужно, только сверить, что джойн использует ту же таблицу

## Критерии готовности (DoD)

- [x] Снапшот включает состояние `TranscriptionJob` кандидата (готовность транскрипта меняет
      значение поля).
- [x] Юнит-тест: `TranscriptionJob` переходит `PENDING → DONE` → `needs_profile_rebuild` возвращает
      `True`, даже если остальные 5 полей не изменились.
- [x] Существующие тесты `change_detection.py`/`candidate_facts.py` не сломаны.
- [ ] Проверено на staging на реальном `TranscriptionJob(DONE)` — профиль кандидата
      пересобрался, `_video_facts` попали в `CandidateProfile.facts`.

## Как проверить

```bash
pytest tests/services/test_change_detection.py -v
pytest tests/services/test_candidate_facts.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг).

## Журнал

- 2026-09-09: `compute_current_sources_snapshot()` — 6-е поле снапшота `video_transcript_finished_at`
  (`MAX(TranscriptionJob.finished_at)` через join `testchecks_transcriptionjob` →
  `testchecks_answer` → `testchecks_testattempt` по `candidate_id`, паттерн как у `max_answer_id`).
  `CHANGE_DETECTION_TABLES` (`platform_db.py`) дополнен `testchecks_transcriptionjob` (раньше был
  только в `CANDIDATE_FACTS_TABLES`) — теперь используется той же таблицей reflection и в
  `scheduler.py`/`job_detection.py`. Новый юнит-тест `test_stale_when_video_transcript_finishes`
  (`test_change_detection.py`) — PENDING→DONE меняет снапшот, остальные 5 полей неизменны →
  `needs_profile_rebuild` = `True`. Существующие фикстуры `_platform_base` (test_change_detection.py,
  test_candidate_facts.py, test_job_detection.py) дополнены таблицей/колонкой
  `testchecks_transcriptionjob.finished_at` — без неё reflect(only=CHANGE_DETECTION_TABLES) падал.
  `pytest tests/` — 190 passed. Staging-шаг (DoD п.4) не выполнен — ждёт деплоя E14-01/02/03 и
  реального `TranscriptionJob(DONE)`.
