# Шаг E2-03 — Alembic-ревизия 0002: `ai_candidate_profile`

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E2-02
**Перед началом:** `03_TDD.md` («Migration Plan») изначально предполагал одну ревизию
`0001_initial` на `ai_vacancy_profile`+`ai_candidate_profile`+`ai_resume_extract` разом.
По факту (эпик E1) каждый эпик получил свою ревизию — `0001_ai_vacancy_profile` уже
применена. Эта практика лучше соответствует правилу «каждый эпик отдельно тестируем и
деплоим независимо» из того же раздела — продолжаем её, эта ревизия здесь
`0002_ai_candidate_profile`. Не противоречит архитектуре (та же схема, тот же
`ai_`-префикс, те же `ondelete='CASCADE'`), просто более мелкий шаг, чем предполагалось
изначально.

## Цель

Ревизия `0002_ai_candidate_profile` создаёт таблицу с двумя FK
(`ondelete='CASCADE'`) на `courses_application`/`headhunter_hhnegotiationrecord`.

## Что сделать

**Step 1: Сгенерировать ревизию**

Run: `uv run alembic revision -m "ai_candidate_profile"`

**Step 2: Написать `upgrade`/`downgrade` вручную**

```python
def upgrade() -> None:
    op.create_table(
        "ai_candidate_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("hh_negotiation_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("data_completeness", sa.String(length=16), nullable=False, server_default="MINIMAL"),
        sa.Column("sources_snapshot", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "application_id IS NOT NULL OR hh_negotiation_id IS NOT NULL",
            name="ck_candidate_profile_has_anchor",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["courses_application.id"],
            name="fk_candidate_profile_application", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["hh_negotiation_id"], ["headhunter_hhnegotiationrecord.id"],
            name="fk_candidate_profile_hh_negotiation", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_candidate_profile_application_id", "ai_candidate_profile", ["application_id"])
    op.create_index("ix_candidate_profile_hh_negotiation_id", "ai_candidate_profile", ["hh_negotiation_id"])


def downgrade() -> None:
    op.drop_table("ai_candidate_profile")
```

**Step 3: Прогнать синтаксическую проверку**

Run: `uv run alembic -x sqlalchemy.url=sqlite:///./_migration_check.db upgrade head && rm _migration_check.db`
Expected: без ошибки. Если `CheckConstraint`/составной FK на несуществующую в SQLite
таблицу упадёт — заменить проверку на `alembic upgrade head --sql` (просмотр DDL без
применения), как в эпике E1.

**Step 4: Commit**

```bash
git add migrations/versions/0002_ai_candidate_profile.py
git commit -m "feat: add Alembic revision 0002 for ai_candidate_profile"
```

*(Реальное применение на прод-Postgres — E2-07, отдельно, с подтверждением.)*

## Файлы

- `migrations/versions/0002_ai_candidate_profile.py` — создать

## Критерии готовности (DoD)

- [ ] Синтаксическая проверка на SQLite/`--sql` без ошибок

## Как проверить

```bash
uv run alembic -x sqlalchemy.url=sqlite:///./_migration_check.db upgrade head && rm _migration_check.db
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
