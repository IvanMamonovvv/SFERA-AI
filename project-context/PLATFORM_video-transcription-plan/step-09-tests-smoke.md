# Step 09 — Тесты и smoke

**Статус:** ✅ DONE (автотесты + все 4 ручных smoke-пункта пройдены живым прогоном 2026-09-09)
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
- [x] Кандидат записал нормальную визитку → через 1–5 мин у HR summary + транскрипт. **Пройдено 2026-09-09** — см. журнал ниже (реальное видео с прод-БД, полный `claim_batch`/`_process_job`).
- [x] Кандидат записал 1 сек тишины / закрыл камеру → у HR «ничего не сказал / речь не распознана»,
      джоб сразу DONE, не пусто и не завис в retry. **Пройдено 2026-09-09.**
- [x] 5 кандидатов завершили почти одновременно → все 5 обработались, платформа не тормозила. **Пройдено 2026-09-09.**
- [x] Перезапуск воркера в середине обработки → джоб доводится (reaper), не теряется. **Пройдено 2026-09-09.**

## Критерий готовности

- [x] Тесты зелёные (`manage.py test` — 657 passed, 3 skipped, регрессий нет), кейс «пустое видео» покрыт явно.
- [x] Пункты добавлены в `project-context/06_TEST_CHECKLIST.md`.

## Журнал
- `2026-09-09` (обновление) — по явному разрешению владельца пройден живой smoke
  главного пункта («нормальная визитка → summary+транскрипт»), полным путём воркера,
  не отдельными функциями. **Важная находка перед началом**: `04_STATE.md` этого
  репозитория утверждал, что код E14-01…08 «не закоммичен» — на деле весь код давно
  смерджен в `main` `FullSphera/sfera_backend` (PR #111–126), рабочая копия чистая
  (`git status` — clean). Запись в STATE была устаревшей/неверной, исправлена отдельно.
  Ход прогона: `.venv` в `FullSphera/sfera_backend` не имел `faster-whisper` —
  доустановлен (`pip install -r sfera_backend/requirements.txt`, `ctranslate2`/`av`/
  `onnxruntime` подтянулись без проблем); юнит-тесты транскрибации в этом venv — 17/17
  зелёных. Локальная sqlite не имела применённых миграций `testchecks.0009`/`0010` —
  прогнан `manage.py migrate`. Реальное видео — по указанию владельца подключился по
  `ssh sfera` (root) к прод-VPS, read-only SQL-запрос к контейнеру `sfera-staging-db-1`
  (`SELECT ... FROM testchecks_answer JOIN testchecks_question WHERE is_video_intro=true
  ...`) нашёл 5 реальных видеовизиток, взят один файл (`answer_video/5632/434/
  e25365102b094f529b3a13fee4ad1763.webm`, кандидат Ольга Войнич), скачан из боевого S3
  (`s3.twcstorage.ru`, креды уже были в `.env` backend) во временный scratchpad-файл.
  `transcribe_video()` (faster-whisper, локально, модель `small`) — реальный русский
  текст распознан корректно (имена, компании SAP/Oracle/Microsoft, термины). LLM-пересказ
  — `PROXY_API_KEY` (proxyapi.ru) в `.env` backend отсутствует; по решению владельца
  вместо него временно использован `OPENROUTER_API_KEY` (нашёлся в `.env` самого
  SFERA-AI, не backend) — `ProxyLLMProvider` OpenAI-совместимый, переключён через
  `PROXY_API_BASE=https://openrouter.ai/api/v1` + `SUMMARY_MODEL=openai/gpt-4o-mini`,
  ключ передавался через переменные окружения процесса (не печатался, temp-файл в
  scratchpad удалён сразу после использования, не коммитился). Итог: собран минимальный
  реальный фикстур (Company/Course/Test/Question/TestAttempt/Answer с `file.name`,
  указывающим на реальный S3-ключ) в **локальной dev sqlite**, `TranscriptionJob(PENDING)`
  создан, `claim_batch()` + `_process_job()` (не по отдельности, весь путь воркера)
  реально скачали видео, транскрибировали, пересказали — `status=DONE`,
  `transcript_text`/`summary_text` заполнены корректным текстом на русском, `error=''`.
  Тестовые записи после прогона удалены (`.delete()`), прод/staging БД не менялась (был
  только `SELECT`). **Открытый вопрос владельцу**: боевой ключ для `PROXY_API_KEY`
  (proxyapi.ru) так и не проверен — прод должен использовать реальный
  `SUMMARY_PROVIDER=proxy`/proxyapi, а не OpenRouter-заглушку; нужно решить, ставить ли
  сразу OpenRouter в прод (тогда `SUMMARY_PROVIDER`/`PROXY_API_BASE`/`SUMMARY_MODEL`
  step-10 надо поменять) или доставать отдельный ключ proxyapi. Остальные 3 ручных
  smoke-пункта закрыты сразу же следующим прогоном (см. ниже).
- `2026-09-09` (продолжение) — закрыты оставшиеся 3 ручных smoke-пункта, все реальными
  вызовами (без моков) через ту же связку faster-whisper + OpenRouter:
  1. **Тишина** — синтетическое 2-секундное видео (чёрный кадр + `anullsrc`, сгенерировано
     `ffmpeg` локально, не требует реального кандидата) → `transcribe_video()` реально дал
     `is_empty=True`, `text=''`; `summarize_transcript('', True)` вернул сообщение о тишине
     без вызова LLM (не через мок `requests.post`, а через реальный ранний return в коде).
  2. **5 кандидатов одновременно** — 5 реальных `TranscriptionJob(PENDING)` (фикстуры:
     Company/Course/Test/Question/TestAttempt/Answer, все ссылаются на тот же реальный
     S3-файл, что и в основном прогоне), `claim_batch(10)` реально забрал все 5 без
     дублей, `ThreadPoolExecutor(max_workers=5)` (тот же код, что в самой команде)
     обработал все параллельно — все 5 дошли до `DONE` за ~94 сек, воркер не упал.
     Оговорка: локальная sqlite не даёт настоящей Postgres-семантики
     `select_for_update(skip_locked=True)` (та же оговорка, что и в E14-08) — проверена
     параллельная обработка и отсутствие дублей на уровне приложения, не сама
     row-level блокировка на Postgres.
  2. **Перезапуск воркера в середине обработки** — джоб переведён в `PROCESSING` с
     `locked_at` в прошлом (старше `TRANSCRIBE_JOB_TIMEOUT_MINUTES`), как после реального
     краша процесса; `reap_stale_jobs()` (реальный вызов, не мок) вернул его в `PENDING`
     (`attempts+=1`), новый `claim_batch`+`_process_job` реально довёл его до `DONE` с
     корректным транскриптом. Отдельно проверена вторая ветка: джоб с
     `attempts=TRANSCRIBE_MAX_ATTEMPTS-1` после `reap_stale_jobs()` стал `FAILED`.
  Все тестовые записи (Company/Course/.../TranscriptionJob) удалены после каждого
  прогона, прод/staging БД не менялись. Ключ `OPENROUTER_API_KEY` передавался только
  через переменные окружения процесса, temp-файл в scratchpad удалён сразу после
  использования. **Все 4 ручных smoke-пункта step-09 закрыты живым прогоном.**
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
