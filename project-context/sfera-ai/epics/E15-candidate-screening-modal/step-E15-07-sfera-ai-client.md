# Шаг E15-07 — HTTP-клиент к SFERA-AI + секрет

**Статус:** TODO
**Слой:** Backend (`sfera_backend`) · **Зависит от:** —
**Репозиторий:** `sfera_backend` — требует отдельного явного разрешения владельца
перед стартом (`CLAUDE.md`).
**Перед началом:** прочитай в `FullSphera/sfera_backend/`:
`sfera_backend/integrations/headhunter/client.py`,
`sfera_backend/integrations/wazzup/client.py` (паттерн `integrations/<service>/client.py`);
в SFERA-AI — `src/sfera_ai/api/app.py` (`make_bff_secret_dependency`, уже существующий
`bff_shared_secret`, которым защищён весь API SFERA-AI).

## Цель

Новый HTTP-клиент в FullSphera для вызова SFERA-AI, с общим секретом — до этого шага
интеграции backend→SFERA-AI не существует вообще (подтверждено — поиск по репозиторию
не нашёл ни base URL, ни секрета).

## Что сделать

1. Новый модуль `sfera_backend/integrations/sfera_ai/client.py` — методы под три
   вызова из E15-06 (screening list, vacancy-profile, export).
2. Секрет `SFERA_AI_SHARED_SECRET` (или аналогичное имя) в `settings.py`/`.env` — по
   паттерну `HH_CLIENT_SECRET`. Значение должно совпадать с `bff_shared_secret`,
   настроенным на стороне SFERA-AI (`Settings().bff_shared_secret`) — согласовать
   единый секрет между двумя сервисами при деплое.
3. Base URL SFERA-AI — новая переменная окружения (внутренний docker-адрес, см.
   `03_TDD.md` этого репозитория, раздел «Инфраструктура и сеть», общая docker-сеть
   `ai_shared`).

## Файлы

- `sfera_backend/integrations/sfera_ai/client.py` — новый.
- `sfera_backend/sfera_backend/settings.py` — новые settings.
- `.env.example` — новые переменные.

## Критерии готовности (DoD)

- [ ] Клиент отправляет секрет в заголовке, который ожидает `make_bff_secret_dependency`
      на стороне SFERA-AI.
- [ ] Сетевая ошибка/таймаут до SFERA-AI не роняет запрос HR без внятной ошибки.
- [ ] Тест на клиент (моки `requests`/`httpx`, по образцу `test_hh_client.py`).

## Как проверить

```bash
python manage.py test integrations.sfera_ai
```

## Как отметить выполнение

1. Журнал в этом файле. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` этого репозитория.

## Журнал

- (не начато — ждёт отдельного разрешения владельца на правку `sfera_backend`)
