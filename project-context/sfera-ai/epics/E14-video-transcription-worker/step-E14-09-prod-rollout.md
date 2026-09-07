# Шаг E14-09 — Prod rollout

**Статус:** TODO
**Слой:** DevOps/Backend · **Зависит от:** E14-01…08
**Репозиторий:** `sfera_backend` (VPS-деплой) — требует отдельного явного разрешения
владельца перед стартом (`CLAUDE.md`), затрагивает прод.
**Перед началом:** прочитай `project-context/PLATFORM_video-transcription-plan/step-10-prod-rollout.md`
(env, деплой воркера, cutover, откат, DoD).

## Цель

Видеовизитки реально обрабатываются на проде, HR видит транскрипт + пересказ.

## Где делать

`sfera_backend` — образ (добавить `faster-whisper`, ffmpeg уже есть), `docker-compose`
(новый сервис-воркер по образцу `scheduler`), env (`TRANSCRIBE_PROVIDER=local`,
`SUMMARY_PROVIDER=proxy`, `SUMMARY_MODEL=gpt-4o-mini`, `PROXY_API_KEY`,
`TRANSCRIBE_ENABLED`).

## Файлы

- `sfera_backend/Dockerfile`/`docker-compose.staging.yml` (единственное согласованное
  исключение уже есть для общей docker-сети — этот шаг про новый сервис-воркер, отдельное
  разрешение всё равно нужно)

## Критерии готовности (DoD)

Полный список — в `step-10-prod-rollout.md`. Кратко:
- [ ] На проде видеовизитки обрабатываются, HR видит summary.
- [ ] Способ выключить фичу одним env/остановкой контейнера есть.

## Как отметить выполнение

1. Журнал в `step-10-prod-rollout.md`.
2. Статус здесь → `DONE`, эпик E14 завершён — обнови `01_STATE.md` внешнего плана и
   `04_STATE.md` этого репозитория.

## Журнал

- (пусто)
