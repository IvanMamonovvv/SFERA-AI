# Step 05 — Воркер `run_transcription_worker` (очередь, concurrency, retry)

**Статус:** ⬜ TODO
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
            3. SummaryProvider.summarize → summary, verdict
            4. сохранить: transcript_text, summary_text, verdict, is_empty,
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

Отдельная периодическая проверка (можно в `core/scheduler.py`): `PROCESSING` с `locked_at` старше N минут
→ вернуть в `PENDING` (воркер упал/перезапущен). Ограничить `attempts`, чтобы не крутить вечно.

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
- (пусто)
