# Шаг E11-01 — HTTP-туннель к backend для локальной разработки

**Статус:** DONE
**Слой:** Infra/DevOps · **Зависит от:** E0-04 (SSH-туннель к БД, паттерн)
**Перед началом:** прочитай `scripts/tunnel-platform-db.sh` (паттерн туннеля через
socat-proxy в сети `ai_shared` + `ssh -L`), раздел «Инфраструктура и сеть» `03_TDD.md`.

## Контекст

`run_full_course_screening.py` (E10-01) при прогоне с локальной машины падает на
resume-extraction: `hh_client` ходит на `settings.hh_backend_base_url`, который
резолвится только изнутри docker-сети `ai_shared` на VPS (внутреннее docker DNS-имя
backend-контейнера). С локальной машины — `[Errno 8] nodename nor servname provided`.
Обнаружено 2026-09-01 на реальном прогоне course_id=39: 82/82 resume-extraction упали
именно так, весь прогон fit-scoring прошёл без резюме, только по анкете.

Побочно найдено: `sfera-staging-backend-1` был отключён от сети `ai_shared`
(аналогично истории с `db`-контейнером, `03_TDD.md`/`project_backend_internal_network_access`) —
переподключён вручную 2026-09-01, но это не решает доступ **с локальной машины**, только
внутри VPS.

## Цель

Есть скрипт (по образцу `tunnel-platform-db.sh`), который поднимает локальный HTTP-туннель
к backend-контейнеру на VPS, аналогично туннелю к БД — чтобы `run_resume_pipeline.py`/
`run_full_course_screening.py`/любой ручной прогон с локальной машины реально мог дёргать
`HHClient`.

## Что сделать

1. Новый `scripts/tunnel-backend.sh` — по паттерну `tunnel-platform-db.sh`: socat-proxy
   на VPS в сети `ai_shared`, слушает `backend-контейнер:8000`, публикует на
   `127.0.0.1:<PROXY_PORT>`; локальный `ssh -L` пробрасывает `localhost:<LOCAL_PORT>` →
   proxy. Отдельные имена контейнера/портов от db-туннеля (не конфликтовать при
   одновременном использовании обоих).
2. `cleanup()` trap на `docker rm -f` proxy-контейнера — обязательно, история с
   `ai-db-tunnel-proxy`, забытым висящим на VPS (2026-09-01, инцидент от второго
   разработчика), не должна повториться.
3. Идемпотентность — как в `tunnel-platform-db.sh`, не поднимать второй туннель, если
   локальный порт уже слушается.
4. Не трогать `.env`/`hh_backend_base_url` в коде сервиса — туннель должен быть
   прозрачным способом временно подменить `HH_BACKEND_BASE_URL` через переменную
   окружения при ручном локальном прогоне (не менять default в `config.py`).

## Файлы

- `scripts/tunnel-backend.sh` — новый скрипт (копия-адаптация `tunnel-platform-db.sh`)

## Критерии готовности (DoD)

- [x] Скрипт поднимает туннель, идемпотентен при повторном запуске
- [x] `cleanup()` trap подтверждён — после `Ctrl+C`/штатного завершения proxy-контейнер
      на VPS реально удаляется (не остаётся висеть)
- [x] Ручной тест: через туннель `HHClient` реально получает ответ от backend (не 404/DNS-ошибка)

## Как проверить

```bash
./scripts/tunnel-backend.sh &
HH_BACKEND_BASE_URL=http://localhost:<LOCAL_PORT> uv run python -c "
from sfera_ai.config import Settings
from sfera_ai.integrations.hh_client import HHClient
settings = Settings()
client = HHClient(base_url=settings.hh_backend_base_url, login=settings.hh_backend_admin_login,
                   password=settings.hh_backend_admin_password, company_slug=settings.hh_backend_company_slug,
                   host_header=settings.hh_backend_host_header)
# любой лёгкий запрос, подтверждающий связь
"
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг).

## Журнал

- 2026-09-01: `scripts/tunnel-backend.sh` создан по паттерну `tunnel-platform-db.sh` —
  socat-proxy на VPS в сети `ai_shared` (порт `18000` по умолчанию), локальный
  `ssh -L localhost:8001 -> proxy` (порты/имена отдельные от db-туннеля:
  `ai-backend-tunnel-proxy` vs `ai-db-tunnel-proxy`). `.env`/`config.py` не тронуты.
  Ручная проверка:
  - идемпотентность — второй запуск при уже поднятом туннеле сразу выходит с
    "Туннель уже поднят на localhost:8001 — ничего не делаю." (exit 0), второй
    ssh/proxy не плодит;
  - `cleanup()` trap подтверждён — после завершения ssh-процесса (SIGTERM,
    эмулирует Ctrl+C) локальный порт закрывается, `docker rm -f
    ai-backend-tunnel-proxy` на VPS отрабатывает без ошибок в логе;
  - через туннель (`HH_BACKEND_BASE_URL=http://localhost:8001`) `HHClient._authenticate()`
    реально получил токен от backend (`AUTH OK, token got: True`) — до этого curl на
    `/api/v1/auth/token/` вернул `400` (валидация тела), не 404/DNS-ошибку, что
    подтвердило: backend отвечает через туннель.
