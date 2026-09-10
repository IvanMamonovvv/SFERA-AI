# Шаг E18-02 — retry транспортной ошибки в HHClient.get_resume_pdf

**Статус:** DONE
**Слой:** Backend · **Зависит от:** нет (независим от E18-01a/b/c, логически шаг B эпика E18)
**Перед началом:** прочитай `integrations/hh_client.py` (`HHClient._get`, `get_resume_pdf`),
`providers.py::OpenRouterClient._request_with_retry` (уже сделанный образец фикса,
коммит `8e1363e`), `services/resume_fetch.py::_fetch_hh_resume` (ловит `HHClientError`
→ `ResumeFetchError` → `ResumeExtract.status=FAILED`).

## Проблема

`OpenRouterClient` уже получил retry на `httpx.RemoteProtocolError` (сервер молча
закрывает keep-alive соединение — 34/35 `FAILED` резюме на staging упали именно на этом,
`04_STATE.md`). `HHClient.get_resume_pdf` той же болезни подвержен, но фикса не получил —
разовый обрыв соединения к backend'у (внутренняя docker-сеть, но всё равно HTTP поверх TCP)
уводит резюме в `FAILED` без повтора, даже если E18-01b/c уже доставляют вызов до `HHClient`
каждый тик.

## Цель

Один разовый сетевой обрыв при скачивании резюме с HH не роняет `ResumeExtract` в `FAILED` —
запрос повторяется один раз по новому соединению, как уже сделано для OpenRouter.

## Что сделать

1. **`HHClient`** — завести приватный хелпер `_get_with_retry(url, headers)`,
   оборачивающий `self._http.get(url, headers=headers)`: при `httpx.RemoteProtocolError`
   один повтор по новому соединению из пула (точное зеркало
   `providers.py::OpenRouterClient._request_with_retry`, не любой `httpx.HTTPError` —
   иначе повторяются и не-транспортные сбои, которые повторять бессмысленно).
2. **`HHClient._get`** — заменить оба прямых вызова `self._http.get(...)` (первый запрос
   и повтор после `_authenticate()` на 401) на `_get_with_retry(...)`. Логика 401→re-auth
   не меняется, просто обёртка над каждым HTTP-вызовом.
3. Публичный контракт `get_resume_pdf`/`HHClientError` не меняется — вызывающий код
   (`resume_fetch.py`) не трогать.

## Файлы

- `src/sfera_ai/integrations/hh_client.py` — `HHClient._get`, новый `_get_with_retry`.

## Критерии готовности (DoD)

- [ ] `httpx.RemoteProtocolError` на первой попытке `_get_with_retry` → второй вызов
  того же `self._http.get` по новому соединению → успех, `get_resume_pdf` не падает.
- [ ] `httpx.RemoteProtocolError` на ОБЕИХ попытках → `get_resume_pdf` по-прежнему
  бросает `HHClientError` (поведение не хуже текущего, просто с одной доп. попыткой).
- [ ] Существующий путь 401 → `_authenticate()` → повтор запроса — не сломан
  (регрессия на уже покрытую логику re-auth).
- [ ] Не-транспортные ошибки (`httpx.HTTPError`, отличные от `RemoteProtocolError`,
  например обычный timeout `httpx.ConnectTimeout`) НЕ повторяются — retry только на
  тот конкретный обрыв, что уже наблюдался в проде.
- [ ] `uv run pytest` — весь сьют зелёный, регрессий нет.

## Как проверить

```bash
uv run pytest tests/integrations/test_hh_client.py -v  # новый файл теста
uv run pytest  # полный сьют, регрессии
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`
(следующий шаг эпика — E18-03, если владелец даст отдельное «начинай»).

## Журнал

- `2026-09-10` — шаг расписан по запросу владельца (план не был готов на момент
  завершения шага A эпика E18). Реализация не начата — ждёт явного «начинай».
- `2026-09-10` — реализовано: `HHClient._get_with_retry` (зеркало
  `OpenRouterClient._request_with_retry`), оба вызова в `_get` переведены на него.
  4 новых теста в `tests/integrations/test_hh_client.py` (retry-success, retry-exhausted,
  non-transport-not-retried + прогон уже покрытого 401-пути). Полный сьют — 237 passed.
