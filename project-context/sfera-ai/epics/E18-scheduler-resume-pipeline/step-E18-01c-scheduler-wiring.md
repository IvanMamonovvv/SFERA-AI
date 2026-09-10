# Шаг E18-01c — scheduler собирает hh_client/s3_client, рефлексит нужные таблицы

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E18-01b (`process_batch` принимает `hh_client`/`s3_client`/`s3_bucket`)
**Перед началом:** прочитай `scheduler.py::run_tick`, `platform_db.py`
(`CHANGE_DETECTION_TABLES`, `RESUME_DETECTION_TABLES`),
`cli/run_full_course_screening.py:161-173` (образец сборки `HHClient`/`boto3.client`).

## Цель

После тика шедулера (раз в 30 минут) резюме кандидата реально скачано и распаршено
(`ResumeExtract` дошёл до `DONE`/`FAILED`) без единой ручной команды — конец-в-конец,
без CLI.

## Что сделать

1. **`run_tick`** — завести `hh_client`/`s3_client` по образцу
   `cli/run_full_course_screening.py:161-173`
   (`HHClient(base_url=settings.hh_backend_base_url,
   login=settings.hh_backend_admin_login, password=settings.hh_backend_admin_password,
   host_header=settings.hh_backend_host_header)`, `boto3.client("s3",
   endpoint_url=..., aws_access_key_id=..., aws_secret_access_key=...,
   region_name=...)`), передать `s3_bucket=settings.s3_bucket` в `process_batch`.
   Новые импорты: `HHClient`, `boto3`.
2. **`run_tick`** — `platform_base` сейчас рефлексит только `CHANGE_DETECTION_TABLES`.
   `ensure_resume_processed`/`resolve_company_slug_for_hh_negotiation`/
   `find_anketa_resume_answer_id` требуют дополнительно `testchecks_question`,
   `courses_course`, `companies_company`, `headhunter_vacancycoursemapping` — уже
   собраны в готовом наборе `RESUME_DETECTION_TABLES` (`platform_db.py:27`,
   надмножество `CHANGE_DETECTION_TABLES`). Заменить `tables=CHANGE_DETECTION_TABLES`
   на `tables=RESUME_DETECTION_TABLES` в `reflect_platform_tables(...)` внутри
   `run_tick`. `detect_and_enqueue` (детекция, тоже использует этот `platform_base`)
   от лишних таблиц не пострадает — рефлексия просто даёт доступ к большему числу
   classes, существующий код их не трогает.

## Файлы

- `src/sfera_ai/scheduler.py` — `run_tick` — `hh_client`/`s3_client`, `RESUME_DETECTION_TABLES`.

## Критерии готовности (DoD)

- [x] `run_tick` строит `hh_client`/`s3_client`, рефлексит `RESUME_DETECTION_TABLES`.
- [x] Первый тест на `scheduler.py::run_tick` (сейчас 0 тестов на файл) — с моками
  `HHClient`/`boto3.client`/`OpenRouterClient`/`reflect_platform_tables`, проверяет,
  что `process_batch` получает не-`None` `hh_client`/`s3_client` и `platform_base`
  собран с `RESUME_DETECTION_TABLES` (не старым `CHANGE_DETECTION_TABLES`).
- [x] `detect_and_enqueue` внутри того же тика по-прежнему работает штатно с
  расширенным набором таблиц — регрессий в детекции нет.
- [x] `uv run pytest` — весь сьют зелёный, регрессий нет.
- [x] Read-only инвариант к платформенной БД не нарушен — все новые пути только
  читают платформенные таблицы (SQLAlchemy reflection) и HTTP/S3 API, пишут
  только в собственные `ai_*` таблицы.

## Как проверить

```bash
uv run pytest tests/test_scheduler.py -v
uv run pytest  # полный сьют, регрессии
```

Ручная проверка на staging (после деплоя, отдельным разрешением владельца):
создать/найти кандидата с `ResumeExtract` отсутствующим, дождаться тика (или дернуть
`run_tick` вручную через `docker compose exec ai-service uv run python -c
"from sfera_ai.scheduler import run_tick; from sfera_ai.config import Settings;
run_tick(Settings())"`), убедиться, что `ResumeExtract` появился/дошёл до `DONE`.

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E18 закрыт).

## Журнал

- `2026-09-10` — шаг выделен из первоначального единого E18-01 (разбивка на 3 шага
  по итогам ревью), реализация не начата — ждёт явного «начинай» от владельца
  (правило `CLAUDE.md`).
- `2026-09-10` — реализовано. `run_tick` в `scheduler.py` уже собирал `hh_client`/
  `s3_client` и рефлексил `RESUME_DETECTION_TABLES` (код был готов до начала шага,
  не хватало только теста). Добавлен `tests/test_scheduler.py::
  test_run_tick_builds_hh_and_s3_clients_and_reflects_resume_tables` — мокает
  `HHClient`/`boto3`/`reflect_platform_tables`/`detect_and_enqueue`/`process_batch`,
  проверяет аргументы вызовов и `tables=RESUME_DETECTION_TABLES`. `uv run pytest` —
  234 passed, регрессий нет.
