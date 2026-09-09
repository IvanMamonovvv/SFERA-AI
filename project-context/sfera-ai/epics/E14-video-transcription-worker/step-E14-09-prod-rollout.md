# Шаг E14-09 — Prod rollout

**Статус:** DONE (2026-09-09)
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

- `2026-09-09` — выполнено по явному разрешению владельца. Код: PR #128 в
  `sfera_backend` (ветка `feat/e14-09-transcribe-worker-service`, смёржен в `main`) —
  новый сервис `transcribe-worker` в `docker-compose.staging.yml` (по образцу
  `scheduler`, `python manage.py run_transcription_worker`, `cpus: "2"`, том
  `media_volume_staging`); `.env.example` документирует все переменные
  (`TRANSCRIBE_*`/`WHISPER_MODEL_SIZE`/`SUMMARY_*`/`PROXY_API_BASE`). По правке
  владельца переменная секрета — `OPENROUTER_API_KEY` (не `PROXY_API_KEY`,
  значение реально от OpenRouter) — переименована в `summary.py` (env var), сам
  модуль-level константа `PROXY_API_KEY` в коде осталась (используется как bearer
  token для любого прокси-провайдера). Dockerfile/requirements.txt не менялись —
  `faster-whisper`/`ffmpeg` уже были добавлены в E14-02.

  Деплой на VPS выполнен владельцем (`git pull` + `docker compose up -d --build`
  на `/var/www/sphera-backend`, `docker-compose.staging.yml`, проект
  `sfera-staging`). Проверено мной по SSH (`ssh sfera`, разрешение дано явно):
  контейнер `transcribe-worker` поднят, 0 рестартов; env внутри контейнера —
  `TRANSCRIBE_ENABLED=True`, `TRANSCRIBE_PROVIDER=local`,
  `WHISPER_MODEL_SIZE=small`, `SUMMARY_PROVIDER=proxy`,
  `SUMMARY_MODEL=openai/gpt-4o-mini`, `PROXY_API_BASE=https://openrouter.ai/api/v1`,
  `OPENROUTER_API_KEY` установлен (значение не читал/не печатал).

  Живой smoke на реальном видео: взял существующую видеовизитку без джобы
  (`Answer.id=17576`), создал `TranscriptionJob(status=PENDING)` — воркер
  подхватил в течение poll-интервала, `PENDING→PROCESSING→DONE` за ~64с
  (13:15:04→13:16:08), `is_empty=False`, `attempts=0`, `transcript_text` 982
  символа, `summary_text` — связный русский пересказ через реальный вызов
  OpenRouter/gpt-4o-mini. Тестовая запись `TranscriptionJob` удалена сразу
  после проверки (PII не осталось). Платформа не пострадала: `/api/v1/docs/` →
  200, все 5 контейнеров проекта (`backend`/`db`/`gateway`/`scheduler`/
  `transcribe-worker`) up.

  Откат подтверждён по конструкции (не тестировался разрушительно): `docker
  compose stop transcribe-worker` останавливает обработку без влияния на
  платформу; `TRANSCRIBE_ENABLED=False` в `.env` + redeploy — останавливает
  постановку новых джоб в очередь (E14-01).

  **Эпик E14 ещё не завершён** — остался **E14-10** (change detection:
  `TranscriptionJob.status=DONE` не попадает в
  `compute_current_sources_snapshot`/`CandidateProfile.facts`, репозиторий
  `SFERA-AI`, свой код, без ограничения на разрешение).
