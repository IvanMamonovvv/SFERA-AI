# Шаг E23-01 — колонки `portrait_text`/`source_url` на `VacancyProfile`

**Статус:** DONE
**Слой:** Backend (SFERA-AI) · **Зависит от:** —
**Перед началом:** прочитай `models/vacancy_profile.py`, `migrations/versions/0001_ai_vacancy_profile.py`
(конвенция `server_default` для NOT NULL текстовых колонок).

## Цель

`VacancyProfile` хранит исходный текст-портрет (не только производный JSON `requirements`) и
опциональную ссылку на источник — чтобы модалку HR можно было предзаполнить тем же текстом,
что человек ввёл, а не JSON.

## Что сделать

1. `models/vacancy_profile.py` — добавить `portrait_text: Mapped[str] = mapped_column(Text,
   nullable=False, default="")` и `source_url: Mapped[str | None] = mapped_column(Text,
   nullable=True)`.
2. Новая Alembic-ревизия — `sa.Column("portrait_text", sa.Text(), nullable=False,
   server_default="")` (обязательно `server_default`, не только ORM `default` — иначе
   `ADD COLUMN NOT NULL` упадёт на существующих строках, см. конвенцию `0001`/`0003`) и
   `sa.Column("source_url", sa.Text(), nullable=True)`.

## Файлы

- `src/sfera_ai/models/vacancy_profile.py` — новые колонки
- `migrations/versions/0011_vacancy_profile_portrait_text.py` — новая ревизия,
  `down_revision = "0010"` (цепочка сейчас заканчивается на `0010_resume_extract_retry.py` —
  проверить актуальность перед созданием, если появились более новые ревизии)

## Критерии готовности (DoD)

- [x] `alembic upgrade head` на чистой и на непустой (с существующими `VacancyProfile`) БД —
      без ошибок
- [x] `alembic downgrade -1` — на SQLite тестовой БД, не на shared staging
      (см. память `[[feedback_no_downgrade_on_shared_db]]`)
- [x] существующие тесты (`tests/services/test_vacancy_profile.py`,
      `tests/cli/test_vacancy_profile_cli.py`) не сломаны — новые колонки nullable/default,
      старые вызовы без них продолжают работать

## Как проверить

```bash
uv run alembic upgrade head
uv run pytest tests/services/test_vacancy_profile.py tests/cli/test_vacancy_profile_cli.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-09-10` — добавлены `portrait_text`/`source_url` в `VacancyProfile` (модель + ревизия
  `0011_vacancy_profile_portrait_text`, `down_revision = "0010"`). `alembic upgrade head` на
  staging прошёл (после того как обнаружился и был исправлен рассинхрон пароля `ai_owner` в
  локальном `.env` — серверный пароль поменялся, не связано с этим шагом). Downgrade
  собственной ревизии проверен изолированно на SQLite (не полной цепочкой — общая цепочка
  0001+ на SQLite падает раньше на постороннем `ALTER COLUMN ... DROP DEFAULT`, известное
  ограничение SQLite, не связано с этой ревизией). Тесты
  `tests/services/test_vacancy_profile.py`, `tests/cli/test_vacancy_profile_cli.py` — 3 passed.
