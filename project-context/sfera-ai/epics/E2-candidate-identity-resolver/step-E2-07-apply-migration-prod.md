# Шаг E2-07 — Применить миграцию на реальном Postgres

**Статус:** TODO
**Слой:** DevOps · **Зависит от:** E2-03, E2-06

**⚠️ Пишет DDL в боевую БД платформы (создаёт таблицу `ai_candidate_profile` + FK на
`courses_application`/`headhunter_hhnegotiationrecord`). Не деструктивно для
существующих данных, но затрагивает прод — подтвердить перед запуском.**

## Цель

Таблица `ai_candidate_profile` реально создана на прод-Postgres, backfill прогнан на
реальных данных без дублей.

## Что сделать

**Step 1: Поднять туннель с `ai_owner`-credentials**

Run: `VPS_USER=<логин> ./scripts/tunnel-platform-db.sh`

**Step 2: Прогнать миграцию**

Run: `WRITE_DATABASE_URL=postgresql+psycopg://ai_owner:<pwd>@localhost:5433/<db> uv run alembic upgrade head`
Expected: `ai_candidate_profile` создана, лог alembic показывает `Running upgrade
0001 -> 0002`.

**Step 3: Прогнать backfill (E2-06) на реальных данных**

Expected: без исключений, без дублей (см. E2-06).

## Файлы

- нет новых файлов — прод-операция

## Критерии готовности (DoD)

- [ ] Миграция применена на прод-Postgres без ошибок
- [ ] Backfill прогнан на реальных данных без дублей

## Как проверить

```bash
uv run python -m sfera_ai.cli.backfill_candidate_profiles
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано, подтверждение владельца перед прод-операцией>.
