# Step 01 — Модель-очередь `TranscriptionJob`

**Статус:** ⬜ TODO
**Зависит от:** можно параллельно с step-00.
**Цель:** durable-очередь в БД — одна строка на видеовизитку, переживает рестарты, безопасна для нескольких воркеров.

## Где

Новое приложение или в существующем `testchecks/` (рекомендуется `testchecks/models.py` — рядом с `Answer`).

## Модель (эскиз, финал — при согласовании)

```python
class TranscriptionJob(CreatedModifiedBaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING'
        PROCESSING = 'PROCESSING'
        DONE = 'DONE'
        FAILED = 'FAILED'

    answer = models.OneToOneField(          # одна видеовизитка = одна задача (идемпотентность)
        'testchecks.Answer', on_delete=models.CASCADE, related_name='transcription_job'
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    transcript_text = models.TextField(blank=True, default='')   # результат whisper
    summary_text = models.TextField(blank=True, default='')      # результат LLM
    verdict = models.CharField(max_length=32, blank=True, default='')  # напр. TARGET / NON_TARGET / NO_DATA
    is_empty = models.BooleanField(default=False)                # речь не распознана (тишина/пусто)
    attempts = models.PositiveSmallIntegerField(default=0)       # для retry с backoff
    error = models.TextField(blank=True, default='')
    locked_at = models.DateTimeField(null=True, blank=True)      # для reap «зависших» PROCESSING
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['status', 'created_at'])]  # быстрый pull PENDING FIFO
```

## Почему так

- `OneToOneField(Answer)` — гарантирует ровно одну задачу на видео, `get_or_create` идемпотентен при повторной постановке.
- `status + created_at` индекс → воркер быстро берёт старейшие PENDING.
- `attempts` + `error` → повторные попытки при сбое whisper/LLM/сети.
- `locked_at` → джоб-«ревайвер»: PROCESSING старше N минут (воркер упал) вернуть в PENDING.
- **Не храним транскрипт в самой `Answer`** — чтобы не трогать существующую модель ответов (правило «не ломать»).

## Действия

1. Добавить модель в `testchecks/models.py` (+ `verbose_name` для админки).
2. `python manage.py makemigrations testchecks && migrate`.
3. Зарегистрировать в `admin.py` (read-only просмотр очереди для отладки: status, verdict, error).

## Критерий готовности

- [ ] Миграция применяется, откат чистый.
- [ ] `TranscriptionJob.objects.get_or_create(answer=...)` не создаёт дублей.
- [ ] Модель видна в Django-admin (для мониторинга очереди).

## Журнал
- (пусто)
