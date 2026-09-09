# Шаг E16-01 — ai-scheduler отдельным сервисом в docker-compose

**Статус:** DONE
**Слой:** Infra · **Зависит от:** E0 (Dockerfile, shared docker-сеть)
**Перед началом:** прочитай `docker-compose.yml`, `Dockerfile`, `src/sfera_ai/scheduler.py`.

## Цель

Тик очереди (`run_tick`, раз в 30 минут) реально запускается на VPS постоянным процессом —
раньше поднимался только `ai-service` (FastAPI/uvicorn), `scheduler.py` нигде не был
подключён к деплою (найдено 2026-09-09 при обсуждении прод-релиза E15).

## Что сделать

1. Добавить сервис `ai-scheduler` в `docker-compose.yml` — тот же образ (`build: .`), команда
   `["uv", "run", "python", "-m", "sfera_ai.scheduler"]` вместо uvicorn.
2. Явно закрепить инвариант «ровно один инстанс» комментарием в compose-файле — `build_scheduler()`
   вызывается только из `if __name__ == "__main__"` `scheduler.py`, не дублировать вызов в
   `api/app.py` lifespan.

## Файлы

- `docker-compose.yml` — новый сервис `ai-scheduler`, `restart: unless-stopped`.

## Критерии готовности (DoD)

- [x] `ai-scheduler` в `docker-compose.yml`, использует тот же `Dockerfile`, другую `command`.
- [x] Комментарий в compose-файле явно запрещает `--scale ai-scheduler=N>1`.
- [x] `api/app.py` не вызывает `build_scheduler()` — единственная точка инициализации осталась
  в `scheduler.py` (проверено чтением файла).

## Как проверить

```bash
docker compose -p sfera-ai config --services   # ai-service, ai-scheduler
grep -c "build_scheduler()" src/sfera_ai/api/app.py src/sfera_ai/scheduler.py
# app.py — 0 совпадений, scheduler.py — 1 (только в __main__)
```

## Журнал

- `2026-09-09` — выполнено. `SELECT ... FOR UPDATE SKIP LOCKED` в `process_batch`
  (`job_processing.py`) и партиционный уникальный индекс на `AIProcessingJob` (E5-07) уже
  защищают от повторной обработки/постановки одной и той же джобы на уровне БД — второй
  инстанс планировщика не приводит к порче данных, но удваивает реальный AI-бюджет
  (два независимых `CronTrigger` тикают по своим таймерам) — поэтому дисциплина
  «ровно один инстанс» на уровне compose/деплоя, не полагаться только на БД-гарантии.
  Решили не добавлять Postgres advisory lock в код — существующих БД-гарантий достаточно
  для корректности, лишний lock был бы защитой от сценария, которого сам факт единственного
  compose-сервиса без replicas уже не допускает (не усложнять без необходимости).
