# Step 09 — Тесты и smoke

**Статус:** ✅ DONE (автотесты; ручной smoke заведён, не пройден живым видео)
**Зависит от:** реализация step-01…07.
**Цель:** покрыть очередь, воркер и крайние случаи (особенно «пустое видео»).

## Юнит / интеграция (backend)

- [x] Завершение анкеты с видео → создан ровно один `TranscriptionJob(PENDING)` (step-02, идемпотентность) — уже покрыто `test_transcription_enqueue.py` (E14-01).
- [x] Завершение без видео → джоб не создан — там же.
- [x] `claim_batch` + `skip_locked`: два «воркера» не берут один джоб (замокать/симулировать) — новый `test_transcription_worker.py::ClaimBatchTests`.
- [x] Провайдер (замоканный) → джоб DONE, поля заполнены — `ProcessJobTests::test_provider_success_marks_done_with_fields`.
- [x] **Пустое/тихое видео** → `is_empty=True`, LLM не вызывается, summary — сообщение о тишине — `ProcessJobTests::test_empty_video_marks_is_empty_without_llm_call` (проверено мокой `requests.post` — не вызвана).
- [x] Сбой провайдера → attempts++, retry, после MAX → FAILED, воркер не падает — `ProcessJobTests::test_provider_failure_*`.
- [x] Reaper возвращает зависший PROCESSING → PENDING (и FAILED после лимита попыток) — `ReapStaleJobsTests`.
- [x] `clean_expired_videos` не трогает transcript/summary (step-08) — уже покрыто `core/tests/test_retention_guard.py` (E14-07, косвенно через `job.status == DONE`).
- [x] API карточки кандидата отдаёт `transcription`; кандидат не получает (RBAC) — уже покрыто `test_candidate_course_answers_transcription.py` (E14-05).

## Smoke (ручной, добавить в `06_TEST_CHECKLIST.md`)

- [x] Пункты заведены в `project-context/06_TEST_CHECKLIST.md` (раздел «Видео-транскрибация»).
- [ ] Кандидат записал нормальную визитку → через 1–5 мин у HR summary + транскрипт. **Не пройдено** — нет запущенного воркера/реального видео в этой сессии.
- [ ] Кандидат записал 1 сек тишины / закрыл камеру → у HR «ничего не сказал / речь не распознана»,
      джоб сразу DONE, не пусто и не завис в retry. **Не пройдено** (то же ограничение).
- [ ] 5 кандидатов завершили почти одновременно → все 5 обработались, платформа не тормозила. **Не пройдено.**
- [ ] Перезапуск воркера в середине обработки → джоб доводится (reaper), не теряется. **Не пройдено.**

## Критерий готовности

- [x] Тесты зелёные (`manage.py test` — 657 passed, 3 skipped, регрессий нет), кейс «пустое видео» покрыт явно.
- [x] Пункты добавлены в `project-context/06_TEST_CHECKLIST.md`.

## Журнал
- `2026-09-09` — юнит/интеграционные тесты закрыты по явному разрешению владельца на этот
  шаг (код в `sfera_backend`). Новый `testchecks/tests/test_transcription_worker.py` (11
  тестов) покрывает то единственное, что реально не было протестировано ранее (по прямой
  заметке в `04_STATE.md` на E14-04): `claim_batch`, `reap_stale_jobs`, `_process_job`
  (успех/пустое видео/сбой+retry/FAILED после лимита). Остальные DoD-пункты («создание
  джобы», «API-поле», «retention guard не трогает транскрипт») уже были закрыты
  предыдущими шагами (E14-01/05/07) — не дублировались новым файлом. По ходу выяснено:
  `claim_batch`/`reap_stale_jobs` используют `select_for_update(skip_locked=True)`, а
  тестовая БД — sqlite (`connection.features.has_select_for_update = False`); тем не
  менее вызовы в тестах отработали без исключения (Django на sqlite тихо игнорирует
  локировку, а не падает) — **настоящая multi-connection конкурентность не проверена**
  (тест `test_second_worker_does_not_reclaim_already_processing_job` симулирует два
  воркера последовательными вызовами в одной транзакции, как явно разрешает
  формулировка DoD «замокать/симулировать»; реальная защита от гонки на PostgreSQL
  проверяется только на проде/staging). Полный прогон `manage.py test` (весь backend,
  не только `testchecks`) — 657 passed, 3 skipped, регрессий нет. Ручной smoke-чеклист
  из §«Smoke» **заведён** в `project-context/06_TEST_CHECKLIST.md`
  (`sfera_backend/project-context/06_TEST_CHECKLIST.md`, а не `project-context2/` —
  проверено по ссылкам из корневого `CLAUDE.md`), но НЕ пройден — нет живого видео и
  запущенного воркера в этой сессии (живой прогон транскрибации всё ещё блокирован тем
  же, что и на E14-02/04: faster-whisper тяжёлая зависимость, реальный видеофайл нужен
  от владельца). Изменения (новый тестовый файл + правка чеклиста) НЕ закоммичены в
  `sfera_backend`/`FullSphera` — только рабочая копия.
