# Step 05 — Воркер `run_transcription_worker` (очередь, concurrency, retry)

**Статус:** 🟡 Код готов, живой прогон — на step-09 (внешний план)
**Зависит от:** step-01, 03, 04.
**Цель:** отдельный процесс, который дренирует очередь `TranscriptionJob`, безопасно параллелится и переживает пики/завалы.

## Команда

`testchecks/management/commands/run_transcription_worker.py` (по образцу `core/.../run_scheduler.py`).

## Ядро: безопасный pull из очереди (без Celery/Redis)

```python
from django.db import transaction

def claim_batch(limit):
    with transaction.atomic():
        jobs = (TranscriptionJob.objects
                .select_for_update(skip_locked=True)          # ← ключ: два воркера не возьмут один джоб
                .filter(status='PENDING')
                .order_by('created_at')[:limit])
        ids = [j.id for j in jobs]
        TranscriptionJob.objects.filter(id__in=ids).update(
            status='PROCESSING', locked_at=timezone.now())
        return ids
```

- `SELECT ... FOR UPDATE SKIP LOCKED` (PostgreSQL) — очередь безопасна при любом числе воркеров/потоков.
- `limit = TRANSCRIBE_CONCURRENCY` — сколько обрабатываем параллельно (из step-00).

## Цикл обработки

```
loop:
    ids = claim_batch(concurrency)
    если пусто → sleep(POLL_INTERVAL, напр. 5–10 с) → continue
    обработать ids параллельно (ThreadPool/ProcessPool = concurrency):
        для job:
            1. answer.file → временный wav (ffmpeg)
            2. TranscriptionProvider.transcribe → transcript, is_empty
            3. SummaryProvider.summarize → summary (без verdict — упрощено владельцем 2026-09-07)
            4. сохранить: transcript_text, summary_text, is_empty,
               status=DONE, finished_at
            при исключении:
               attempts += 1; error=...; 
               status = PENDING (если attempts < MAX) иначе FAILED
```

- **Параллелизм на уровне процессов** предпочтителен для CPU-bound whisper (GIL). Вариант: N дочерних
  процессов, каждый со своей загруженной моделью. Проще — запустить **N реплик контейнера-воркера с concurrency=1**
  (тогда каждый процесс = одно ядро, модель грузится один раз). Выбор — по step-00.
- **Модель whisper грузится один раз** на старте процесса, не на каждый джоб.

## Reaper зависших джобов

Отдельная периодическая проверка (можно в `core/scheduler.py`): `PROCESSING` с `locked_at` старше
`TRANSCRIBE_JOB_TIMEOUT_MINUTES` → вернуть в `PENDING` (воркер упал/перезапущен). Ограничить
`attempts`, чтобы не крутить вечно.

**Как выбрать число (не оставлять текстовым плейсхолдером):** таймаут = p99-время обработки одного
видео (замеряется в step-00 на реальном VPS, длинные видео тоже) **× 3–5** — запас на случай, если
сервер под нагрузкой обрабатывает дольше обычного. Слишком маленький таймаут даёт риск: реальный
воркер ещё не завис, а просто долго обрабатывает — reaper вернёт джоб в очередь, второй воркер
возьмёт тот же файл параллельно, оба допишут в одну строку `TranscriptionJob` (гонка записи,
частичный/битый результат). Конкретное число — зафиксировать в env `TRANSCRIBE_JOB_TIMEOUT_MINUTES`
по факту замера step-00/step-09, до начала step-10 (прод-раскатка).

## Поведение при пиках/завалах (ответ на вопрос владельца)

- 5 кандидатов завершили разом → 5 строк PENDING встали мгновенно. Воркер(ы) берут по `concurrency`,
  остальные ждут в очереди. **Веб не затронут.**
- 50–200 в завале → дренируются со скоростью `concurrency × 3600 / время_обработки` видео/час (см. step-00).
  HR видит результаты по мере готовности; мгновенность не требуется.
- Мало ядер / большой поток → поднять число реплик воркера ИЛИ переключить `TRANSCRIBE_PROVIDER=yandex` (рубильник).

## Деплой воркера

- Отдельный сервис в `docker-compose` (по образцу `scheduler`):
  `command: python manage.py run_transcription_worker`.
- При желании ограничить CPU: `deploy.resources.limits.cpus` — чтобы воркер не отъедал ядра у веба сверх меры.
- Реплик = столько, сколько ядер выделили под транскрибацию (step-00).

## Критерий готовности

- [ ] Джоб проходит PENDING → PROCESSING → DONE, поля заполнены.
- [ ] Два воркера не берут один джоб (проверка `skip_locked`).
- [ ] Сбой провайдера → retry, после MAX → FAILED, воркер живёт дальше.
- [ ] Зависший PROCESSING реапится обратно в PENDING.
- [ ] Веб-latency стабильна при полной очереди (замер).

## Журнал
- `2026-09-07` — реализовано в `sfera_backend` (владелец дал явное разрешение на правку
  репо для E14-04). Файл: `testchecks/management/commands/run_transcription_worker.py`
  (+ `testchecks/management/__init__.py`, `testchecks/management/commands/__init__.py` —
  пакетов не было). Ядро — `claim_batch` (`select_for_update(skip_locked=True)`,
  PENDING→PROCESSING пачкой до `TRANSCRIBE_CONCURRENCY`), `reap_stale_jobs` (PROCESSING
  с `locked_at` старше `TRANSCRIBE_JOB_TIMEOUT_MINUTES` → PENDING, с тем же
  `select_for_update(skip_locked=True)` по одному джобу внутри короткой транзакции —
  защита от двойного реапа), `_process_job` (скачивание `answer.file` во временный файл
  тем же паттерном, что `lessons/services/video_processing.py::_download_to_local_path`
  — S3 напрямую однопоточно/локальный диск через storage API — → `transcribe_video` →
  `summarize_transcript` → `DONE`; исключение → `attempts+=1`, `PENDING` пока
  `attempts < TRANSCRIBE_MAX_ATTEMPTS`, иначе `FAILED`). Параллелизм —
  `ThreadPoolExecutor(max_workers=TRANSCRIBE_CONCURRENCY)`, `close_old_connections()`
  в начале каждой задачи. Env: `TRANSCRIBE_CONCURRENCY=1`, `TRANSCRIBE_MAX_ATTEMPTS=3`,
  `TRANSCRIBE_JOB_TIMEOUT_MINUTES=30` (плейсхолдер до замера p99 на step-00/09, см.
  раздел «Reaper» этого файла), `TRANSCRIBE_POLL_INTERVAL_SECONDS=5`. Контекст для
  `summarize_transcript` (`position` и т.п.) НЕ прокинут — не было в DoD этого шага,
  `SummaryProvider` и так падает на дефолт при пустом `context`. Деплой (docker-compose
  сервис, реплики) — не сделан, вне кода этого шага.
- `2026-09-07` (обновление) — по решению владельца локальная проверка начата раньше
  step-09/10, не отложена. `.venv` репозитория оказался битым (`pip`/интерпретатор
  ссылались на путь `projects/sfera_backend/...` без `FullSphera` — репозиторий
  переносили на диске); по прямому указанию владельца пересоздан с нуля
  (`python3.12 -m venv`, старый сохранён рядом как `.venv.broken-old` вместо
  удаления). `pip install -r requirements.txt` — **faster-whisper тянет ctranslate2,
  НЕ torch** (легче, чем ожидалось изначально в плане). `.env` не понадобился — все
  переменные в `sfera_backend/settings.py` имеют дефолты (`DB_POSTGRES_ON=False` →
  sqlite, `USE_S3_STORAGE=False` → локальный диск). Прогон:
  `python manage.py test testchecks` — 25 passed (включая первый реальный прогон
  тестов E14-02/E14-03, до этого только `ast.parse`/`py_compile`); полный сьют
  `python manage.py test` — **637 passed, 3 skipped, регрессий нет** (новый пакет
  `testchecks/management/` не ломает остальное). Живого видео (реальный whisper +
  реальный LLM-вызов) в этом прогоне НЕ было — только юнит-тесты на моках, живой
  прогон видео/summary всё ещё на step-09 (нужны `PROXY_API_KEY`,
  `TRANSCRIBE_ENABLED=true`, реальный видеофайл). Тестов на сам
  `run_transcription_worker.py` (E14-04) ещё нет — это объём E14-08.
