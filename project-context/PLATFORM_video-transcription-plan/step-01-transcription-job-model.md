# Step 01 — Модель-очередь `TranscriptionJob`

**Статус:** ✅ DONE
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

- [x] Миграция применяется, откат чистый (проверено `sqlmigrate` до раскатки, реально
  применена — таблица подтверждена на проде через reflection 2026-08-27).
- [x] `answer = OneToOneField(Answer, ...)` — `get_or_create(answer=...)` не создаёт дублей
  по конструкции поля (`answer_id` UNIQUE REFERENCES подтверждён на реальной таблице).
- [ ] Модель видна в Django-admin — **неактуально**: в `sfera_backend` вообще нет
  `admin.py` ни у одного приложения (Django admin не используется в проекте), пункт плана
  пропущен как не соответствующий стеку.

## Журнал
- `2026-08-27` — владелец закоммитил, запушил (`54eeb94`), влил в `main` через PR #94
  (`e84982c`) и раскатил на прод. Проверка через reflection (SFERA-AI `platform_db.py`,
  свой SSH-туннель к staging Postgres, туннель закрыт после проверки): таблица
  `testchecks_transcriptionjob` реально существует, колонки совпадают с моделью
  (`id, created_at, modified_at, status, transcript_text, summary_text, verdict, is_empty,
  attempts, error, locked_at, started_at, finished_at, answer_id`). Шаг закрыт.
- `2026-08-27` — модель `TranscriptionJob` добавлена в `testchecks/models.py` (по образцу
  соседней `AnswerVideoUpload`, тот же `CreatedModifiedBaseModel`), миграция
  `0009_transcriptionjob.py` сгенерирована `makemigrations`. `sqlmigrate testchecks 0009`
  проверен визуально — DDL чистый. `makemigrations --check --dry-run` показал отдельное
  несвязанное расхождение в `lessons/migrations` (существовало до правки, не тронуто).
