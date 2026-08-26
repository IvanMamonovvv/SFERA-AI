# Шаг E1-02 — Settings: добавить `write_database_url`

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E1-01

## Цель

`Settings` читает второй URL — `WRITE_DATABASE_URL` (роль `ai_owner`, запись в `ai_*`
таблицы), отдельно от read-only `PLATFORM_DATABASE_URL`.

## Что сделать

**Step 1: Расширить падающий тест**

```python
# добавить в tests/test_config.py
def test_settings_reads_write_database_url(monkeypatch):
    monkeypatch.setenv("PLATFORM_DATABASE_URL", "postgresql+psycopg://x:x@localhost/x")
    monkeypatch.setenv("WRITE_DATABASE_URL", "postgresql+psycopg://ai_owner:secret@localhost:5433/sfera")
    settings = Settings()
    assert settings.write_database_url == "postgresql+psycopg://ai_owner:secret@localhost:5433/sfera"
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ValidationError: write_database_url field required`

**Step 3: Добавить поле в `Settings`**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    platform_database_url: str
    write_database_url: str
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Обновить `.env.example`**

```
WRITE_DATABASE_URL=postgresql+psycopg://ai_owner:CHANGE_ME@localhost:5433/CHANGE_ME
```

**Step 6: Commit**

```bash
git add src/sfera_ai/config.py .env.example tests/test_config.py
git commit -m "feat: add write_database_url setting for AI-owned tables"
```

## Файлы

- `src/sfera_ai/config.py` — изменить
- `.env.example` — изменить
- `tests/test_config.py` — изменить

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/test_config.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/test_config.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-26` — выполнено: `write_database_url` добавлен в `Settings`, тест
  `test_settings_reads_write_database_url` зелёный. **Не сделано:** `.env.example` не
  обновлён — файл под глобальным запретом чтения/правки `.env*`, владелец добавит строку
  `WRITE_DATABASE_URL=postgresql+psycopg://ai_owner:CHANGE_ME@localhost:5433/CHANGE_ME`
  сам. Коммит `7586075`.
