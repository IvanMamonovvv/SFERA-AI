# Шаг E3-02 — получение файла резюме (S3 / HH API)

**Статус:** DONE
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

- [x] Оба источника покрыты тестами с моками
- [x] Ошибка сети/404 переводит `ResumeExtract` в `FAILED` с текстом ошибки, не роняет
      процесс

## Как проверить

```bash
uv run pytest tests/services/test_resume_fetch.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — реализовано с двумя корректировками найденного по ходу дизайна
  (согласовано с владельцем, `AskUserQuestion`):
  1. **HH-резюме получаем не прямым HH OAuth2-клиентом**, а собственным HTTP-клиентом
     (`src/sfera_ai/integrations/hh_client.py`) к уже существующему backend-эндпоинту
     `GET /api/v1/companies/{slug}/integrations/hh/negotiations/{pk}/resume.pdf/` —
     подтверждено чтением `sfera_backend` (read-only, локальная копия FullSphera):
     `HHResumePdfView` (`integrations/headhunter/views.py:157`),
     `api/urls.py:287`. Контракт JWT-логина — `POST /api/v1/auth/token/`
     (`api/urls.py:346`, `simplejwt`, `USERNAME_FIELD='email'`). Соответствует
     `03_TDD.md` п.8 («не дублировать HH-токены/клиент, только через существующий
     `get_resume_pdf`»).
  2. **Транспорт — внутренняя docker-сеть `ai_shared`**, не внешний gateway. Backend-
     контейнер (`sfera-staging-backend-1`) подключён к `ai_shared` живой командой
     `docker network connect --alias backend` (как раньше `db` в E0) — без правки
     `docker-compose.staging.yml` и без рестарта контейнера, простоя не было.
  3. **Найдено на реальном прогоне**: `ALLOWED_HOSTS` backend'а не включает docker-имя
     `backend` — запрос по внутренней сети падал `Bad Request (400)`. Без правки
     backend-конфига — клиент шлёт заголовок `Host: sphera-api.ru` (уже в
     `ALLOWED_HOSTS`), настраивается `hh_backend_host_header` в `config.py`.
     Подтверждено живым `POST /api/v1/auth/token/` — `access`/`refresh` получены.
  4. S3-клиент (`boto3`, свои credentials, отдельные от backend'а) — подтверждено живым
     `list_objects_v2` с реальным префиксом `answer_file/`.
  Файлы: `src/sfera_ai/integrations/hh_client.py`, `src/sfera_ai/services/resume_fetch.py`,
  `tests/integrations/test_hh_client.py`, `tests/services/test_resume_fetch.py`.
  Зависимости `httpx`/`boto3` добавлены (`uv add`). Конфиг расширен (`hh_backend_*`,
  `s3_*`) — новые обязательные env-переменные владелец вписал в `.env` сам.
  `uv run pytest` — 37 passed, полный сьют, без регрессий.
