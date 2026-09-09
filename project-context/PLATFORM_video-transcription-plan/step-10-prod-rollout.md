# Step 10 — Prod rollout

**Статус:** ✅ DONE (2026-09-09)
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
SUMMARY_PROVIDER=proxy               # решено 2026-09-09: боевого ключа proxyapi нет,
                                      # используем OpenRouter (OpenAI-совместимый REST,
                                      # ProxyLLMProvider переиспользуется как есть)
SUMMARY_MODEL=openai/gpt-4o-mini     # id модели в неймспейсе OpenRouter
PROXY_API_BASE=https://openrouter.ai/api/v1
PROXY_API_KEY=...                    # значение — OPENROUTER_API_KEY
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
- `2026-09-09` — раскатано на прод (VPS Timeweb). Детали, включая живой прогон
  на реальном видео и env — `SFERA-AI/project-context/sfera-ai/epics/
  E14-video-transcription-worker/step-E14-09-prod-rollout.md`. Сервис
  `PROXY_API_BASE`/секрет назван `OPENROUTER_API_KEY` (не `PROXY_API_KEY`).
