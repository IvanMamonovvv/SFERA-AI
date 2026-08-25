# Шаг E3-02 — получение файла резюме (S3 / HH API)

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E3-01
**Перед началом:** прочитай `03_TDD.md` раздел «Resume Pipeline», «8. Что НЕ ломаем»
(запрет переиспользовать код backend'а — контракт `get_resume_pdf` повторить, не
импортировать).

## Цель

По `ResumeExtract(status=PENDING)` сервис умеет получить сырые байты резюме — либо из
S3 Timeweb (`ANKETA_FILE`, тот же бакет, свои креды `USE_S3_STORAGE`), либо через
собственный HTTP-клиент HH API (`HH_RESUME`).

## Что сделать

1. `boto3`-клиент для S3 (переиспользует конфиг подключения, отдельный от backend'а).
2. Собственный HTTP-клиент HH API повторяющий контракт `get_resume_pdf` (auth,
   endpoint, обработка ошибок/rate-limit) — новый код, не импорт backend-модуля.
3. Функция `fetch_resume_bytes(extract: ResumeExtract) -> bytes`, диспетчер по
   `source_type`.
4. Обработка ошибок: HH API недоступен / файл не найден → `ResumeExtract.FAILED` +
   `error`, не бросать наружу необработанным (см. `03_TDD.md` «Failure Scenarios»).

## Файлы

- `src/sfera_ai/services/resume_fetch.py`
- `src/sfera_ai/integrations/hh_client.py` — собственный HH API клиент
- `tests/services/test_resume_fetch.py` — моки S3/HH, без реальных вызовов

## Критерии готовности (DoD)

- [ ] Оба источника покрыты тестами с моками
- [ ] Ошибка сети/404 переводит `ResumeExtract` в `FAILED` с текстом ошибки, не роняет
      процесс

## Как проверить

```bash
uv run pytest tests/services/test_resume_fetch.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
