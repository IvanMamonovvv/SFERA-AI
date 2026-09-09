# Шаг E14-11 — Race condition retention guard vs воркер (фикс)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E14-07 (retention guard), E14-04 (воркер)
**Репозиторий:** `sfera_backend` — правка сделана по явному разрешению владельца
(«записать баг в новый шаг эпика E14 и приступить к фиксу», 2026-09-09).
**Перед началом:** прочитай `step-E14-07-retention-guard.md` и журнал `04_STATE.md`
за 2026-09-09 (аудит эпика E14, найден агентом `plan-auditor`).

## Цель

Retention guard (`clean_expired_videos`/`check_disk_pressure`) не должен гонять
статус `TranscriptionJob` с воркером, обрабатывающим этот же джоб прямо сейчас.

## Баг (найден аудитом E14, 2026-09-09)

`core/scheduler.py::clean_expired_videos` помечал джоб `FAILED`, если его статус
не `DONE` — без разбора `PENDING`/`PROCESSING`. Воркер (`run_transcription_worker.py
::_process_job`) держит объект джоба в памяти минуты (скачивание видео +
распознавание + LLM-пересказ) и в конце писал `job.save(status=DONE, ...)`
безусловно, без проверки, что джоб всё ещё принадлежит ему.

Гонка на границе 30-дневного retention-лимита: если scheduler-тик срабатывает,
пока джоб в `PROCESSING`, и воркер в этот момент успешно завершает работу —
порядок записей непредсказуем:
- `FAILED` может лечь поверх уже успешно сохранённого `DONE` с заполненными
  `transcript_text`/`summary_text` — HR видит «FAILED», хотя текст в БД есть.
- Из-за `status != DONE` факт видео (`candidate_facts.py::_video_facts`) не
  попадает в `CandidateProfile.facts`/скоринг, при этом `finished_at` уже
  проставлен воркером до гонки → change detection (`video_transcript_finished_at`)
  раз за разом триггерит `needs_profile_rebuild`, каждый раз безрезультатно —
  факт теряется молча, без ретрая.

`check_disk_pressure` мог по той же причине удалить файл видео, ещё
обрабатываемого воркером (`answer.file.delete()` без проверки `PROCESSING`).

Ни `test_retention_guard.py`, ни `test_transcription_worker.py` кейс
«джоб `PROCESSING` в момент retention-тика» не покрывали (только `PENDING`).

## Фикс

1. `core/scheduler.py::clean_expired_videos` — джоб в `PROCESSING` в этот тик
   пропускается целиком (ни статус, ни файл не трогаются). Если воркер реально
   завис — `reap_stale_jobs()` вернёт джоб в `PENDING`/`FAILED` по своему
   таймауту, следующий тик retention-guard обработает штатно.
2. `core/scheduler.py::check_disk_pressure` — та же защита: файл видео с
   джобом в `PROCESSING` не удаляется в этом проходе.
3. `run_transcription_worker.py::_process_job` — финальный успешный save
   заменён на conditional update:
   `TranscriptionJob.objects.filter(pk=job.pk, status=PROCESSING).update(...)`.
   Если джоб к моменту завершения уже не `PROCESSING` (изменён извне) —
   результат не перезаписывает чужое изменение молча, пишется warning-лог.

## Файлы

- `sfera_backend/core/scheduler.py` — `clean_expired_videos`, `check_disk_pressure`
- `sfera_backend/testchecks/management/commands/run_transcription_worker.py` — `_process_job`

## Критерии готовности (DoD)

- [x] `clean_expired_videos`/`check_disk_pressure` не трогают джоб/файл в `PROCESSING`.
- [x] `_process_job` не перезаписывает статус, изменённый извне, молча.
- [x] Существующие тесты (`test_retention_guard.py`, `test_transcription_worker.py`) зелёные —
  `manage.py test testchecks core` → 60 passed, регрессий нет.
- [x] Новые тесты: `test_processing_job_past_hard_limit_skipped`,
  `test_processing_job_video_not_deleted_under_pressure`,
  `test_job_changed_externally_during_processing_does_not_overwrite`.

## Как проверить

```bash
cd /Users/proskurkin-va/Documents/projects/FullSphera/sfera_backend
.venv/bin/python manage.py test core.tests.test_retention_guard testchecks.tests.test_transcription_worker
```

## Журнал

- 2026-09-09 — баг найден `plan-auditor` при полном аудите логики эпика E14 (см.
  `04_STATE.md`). По явному разрешению владельца зафиксирован отдельным шагом и
  сразу пофикшен: `clean_expired_videos`/`check_disk_pressure` пропускают
  `PROCESSING`-джобы, `_process_job` использует conditional `update()` вместо
  безусловного `save()`. 3 новых теста написаны (кейсы: PROCESSING пропущен
  retention-тиком по 30-дневному лимиту, PROCESSING не удаляется при disk
  pressure, финальный DONE не перезаписывает статус, изменённый извне во время
  обработки). `manage.py test testchecks core` — 60 passed, регрессий нет.
  Не закоммичено в `sfera_backend` — правка на диске, ждёт решения владельца
  по коммиту/PR.
