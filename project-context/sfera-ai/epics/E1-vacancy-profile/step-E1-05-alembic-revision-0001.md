# Шаг E1-05 — Alembic-ревизия 0001: `ai_vacancy_profile`

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E1-04

## Цель

Ревизия `0001_ai_vacancy_profile` создаёт таблицу с FK на `courses_course.id`
(`ondelete='CASCADE'`) и partial unique index на `is_current`.

## Что сделать

**Step 1: Сгенерировать ревизию**

Run: `uv run alembic revision -m "ai_vacancy_profile"`

**Step 2: Написать `upgrade`/`downgrade` вручную (не autogenerate — FK на платформенную
таблицу autogenerate не увидит)**

```python
def upgrade() -> None:
    op.create_table(
        "ai_vacancy_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "version", name="uq_vacancy_profile_course_version"),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses_course.id"],
            name="fk_vacancy_profile_course", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_vacancy_profile_course_id", "ai_vacancy_profile", ["course_id"])
    # Частичный индекс: быстрый lookup «текущий профиль» + гарантия ровно одного is_current=True на course
    op.create_index(
        "uq_vacancy_profile_course_current",
        "ai_vacancy_profile",
        ["course_id"],
        unique=True,
        postgresql_where=sa.text("is_current IS TRUE"),
    )


def downgrade() -> None:
    op.drop_table("ai_vacancy_profile")
```

**Step 3: Прогнать на локальной SQLite-проверке синтаксиса (не создаёт partial index,
но проверяет что миграция вообще исполняется)**

Run: `uv run alembic -x sqlalchemy.url=sqlite:///./_migration_check.db upgrade head && rm _migration_check.db`
Expected: команда завершается без ошибки (partial `postgresql_where` в SQLite
игнорируется драйвером Alembic/SQLAlchemy для SQLite backend — если упадёт, заменить
проверку на `alembic upgrade head --sql` для просмотра сгенерированного DDL без
реального применения).

**Step 4: Commit**

```bash
git add migrations/versions/0001_ai_vacancy_profile.py
git commit -m "feat: add Alembic revision 0001 for ai_vacancy_profile"
```

*(Реальное применение на прод-Postgres — E1-09, отдельно, с подтверждением.)*

## Файлы

- `migrations/versions/0001_ai_vacancy_profile.py` — создать

## Критерии готовности (DoD)

- [ ] Синтаксическая проверка на SQLite/`--sql` без ошибок

## Как проверить

```bash
uv run alembic -x sqlalchemy.url=sqlite:///./_migration_check.db upgrade head && rm _migration_check.db
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-26` — ревизия `0001_ai_vacancy_profile.py` написана вручную (upgrade/downgrade
  по шагу, revision id заменён с автосгенерированного hash на `0001` для читаемого
  порядка). Step 3 (`-x sqlalchemy.url=sqlite:...`) не сработал — `migrations/env.py`
  безусловно ставит `sqlalchemy.url` из `Settings().write_database_url`, `-x` не
  учитывается, попытка подключиться к порту 5434 (уже снесённый локальный Postgres из
  E1-01) упала `Connection refused`. Использован запасной вариант из примечания шага:
  `uv run alembic upgrade head --sql` — сгенерированный DDL проверен визуально, корректен
  (SERIAL, FK CASCADE, partial unique index на `is_current`), ошибок нет.
