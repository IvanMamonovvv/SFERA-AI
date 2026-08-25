# Шаг E0-01 — Project scaffold (uv, src-layout)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** —
**Перед началом:** прочитай `03_TDD.md` раздел «1. Обзор решения» (отдельный git-репозиторий,
Python-проект под `uv`), `05_EPICS.md` эпик E0.

## Цель

Минимальный Python-проект под `uv`, src-layout, зависимости SQLAlchemy/psycopg/
pydantic-settings/pytest установлены.

## Что сделать

**Step 1: Инициализировать uv-проект**

Run: `uv init --package --name sfera-ai --python 3.12 .`

Expected: создан `pyproject.toml`, `src/sfera_ai/__init__.py`, `.python-version`.

**Step 2: Добавить зависимости**

```bash
uv add "sqlalchemy>=2.0" "psycopg[binary]>=3.2" "pydantic-settings>=2.5"
uv add --dev pytest
```

Expected: `pyproject.toml` содержит секцию `[project.dependencies]` с тремя пакетами,
`[dependency-groups.dev]` с `pytest`. Появился `uv.lock`.

**Step 3: Обновить `.gitignore`**

```gitignore
.venv/
__pycache__/
*.egg-info/
.env
```

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock .python-version src tests .gitignore
git commit -m "chore: scaffold uv Python project"
```

## Файлы

- `pyproject.toml` — создать
- `src/sfera_ai/__init__.py` — создать
- `src/sfera_ai/py.typed` — создать
- `.python-version` — создать
- `tests/__init__.py` — создать
- `.gitignore` — изменить (добавить `.venv/`, `__pycache__/`, `*.egg-info/`, `.env`)

## Критерии готовности (DoD)

- [x] `uv run python -c "import sfera_ai"` не падает
- [x] `uv.lock` закоммичен

## Как проверить

```bash
uv run python -c "import sfera_ai"
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-26 — uv установлен через brew (0.12.6), `uv init --package` создал pyproject.toml/src-layout/README.
  Добавлены sqlalchemy/psycopg[binary]/pydantic-settings + dev pytest, `uv.lock` создан. `.gitignore` уже содержал
  нужные записи (не менялся). Созданы `src/sfera_ai/py.typed`, `tests/__init__.py`. `uv run python -c "import sfera_ai"`
  прошёл. Коммит `40073bf`.
