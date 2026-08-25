# Step 10 — Prod rollout

**Статус:** ⬜ TODO
**Зависит от:** step-01…09.
**Цель:** безопасно выкатить на VPS (см. `project-context/09_BACKEND_DEPLOY.md`).

## Подготовка сервера

- [ ] Установить `faster-whisper` в образ backend (requirements/pyproject). `ffmpeg` уже есть — проверить.
- [ ] Предзагрузить модель whisper в образ или на volume (чтобы воркер не качал её на первом старте в проде).
- [ ] Проверить свободные RAM/диск под модель (данные из step-00).

## Env (новые переменные)

```
TRANSCRIBE_PROVIDER=local            # local | yandex | proxy  (рубильник)
WHISPER_MODEL_SIZE=small             # из step-00
TRANSCRIBE_CONCURRENCY=2             # из step-00
SUMMARY_PROVIDER=gigachat            # gigachat | proxy
# ключи по выбранным провайдерам:
GIGACHAT_API_KEY=...  / PROXY_API_KEY=...  / YANDEX_STT_KEY=...
TRANSCRIBE_MAX_ATTEMPTS=3
```

## Деплой воркера

- [ ] Добавить сервис в `docker-compose` (по образцу `scheduler`):
      `command: python manage.py run_transcription_worker`, реплик = concurrency-план из step-00.
- [ ] (Опц.) Ограничить CPU воркера через `deploy.resources.limits.cpus`, чтобы не отбирать ядра у веба.
- [ ] Прогнать миграции (`TranscriptionJob`).

## Cutover / первый прогон

- [ ] Выкатить на staging, прогнать smoke (step-09) на реальных видео.
- [ ] Замерить: время обработки, latency платформы под нагрузкой, RAM/своп.
- [ ] Backfill (опционально): поставить в очередь джобы для уже существующих видеовизиток
      (management-команда `enqueue_existing_video_answers`) — контролируемо, батчами, чтобы не завалить воркер.
- [ ] Прод: выкатить, понаблюдать очередь через admin (`TranscriptionJob` статусы), настроить алерт на рост FAILED.

## Откат

- [ ] Фича изолирована: остановить воркер-контейнер → обработка встаёт, платформа работает как раньше.
- [ ] Постановку в очередь (step-02) спрятать за feature-flag env (`TRANSCRIBE_ENABLED`) — чтобы можно
      было выключить триггер без релиза.

## Критерий готовности

- [ ] На проде видеовизитки обрабатываются, HR видит summary.
- [ ] Платформа стабильна под нагрузкой обработки.
- [ ] Есть способ выключить фичу одним env/остановкой контейнера.

## Журнал
- (пусто)
