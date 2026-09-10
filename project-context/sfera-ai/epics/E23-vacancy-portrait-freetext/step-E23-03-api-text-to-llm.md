# Шаг E23-03 — `POST /vacancy-profile/` принимает текст, вызывает LLM-извлечение

**Статус:** DONE
**Слой:** Backend (SFERA-AI) · **Зависит от:** E23-02
**Перед началом:** прочитай `api/routes/vacancy.py` (`create_vacancy_profile`,
`_serialize_vacancy_profile`, сосед `create_feedback` — образец синхронного LLM-вызова в
route), `services/vacancy_portrait.py::build_vacancy_requirements`, `api/deps.py::get_llm_client`.

## Цель

HR (через фронтенд) присылает обычный текст портрета — эндпоинт сам прогоняет его через LLM
(`build_vacancy_requirements`) и получает структурированный `requirements`, без ручного JSON.

## Что сделать

1. `VacancyProfileCreate` (pydantic body) — заменить `requirements: dict[str, Any]` на
   `portrait_text: str`, `source_url: str | None = None` (оставить `notes`, `created_by_id`).
2. В `create_vacancy_profile`:
   - добавить `llm_client: OpenRouterClient = Depends(get_llm_client)`;
   - вызвать `build_vacancy_requirements(body.portrait_text, body.source_url,
     llm_client=llm_client)` **до** `create_vacancy_profile_version` и до
     `threading.Thread(...).start()` — при исключении ничего не должно записаться в БД и
     фоновый пересчёт не должен стартовать;
   - `except InvalidVacancyRequirementsResponse as exc: raise HTTPException(422, str(exc))`;
   - `requirements.pop("source_url", None)` — `build_vacancy_requirements` кладёт `source_url`
     внутрь самого dict `requirements`, это дублирует новую колонку и утечёт в промпт
     fit-scoring как будто реальное требование — убрать перед сохранением, колонка остаётся
     единственным источником правды по `source_url`;
   - передать `requirements`, `portrait_text=body.portrait_text`, `source_url=body.source_url`
     в `create_vacancy_profile_version`.
3. `_serialize_vacancy_profile` — добавить `portrait_text`, `source_url` в ответ (нужно для
   предзаполнения textarea на фронте при повторном открытии модалки).

## Файлы

- `src/sfera_ai/api/routes/vacancy.py` — тело запроса, route handler, сериализатор
- `tests/api/test_vacancy_endpoints.py` — существующие тесты POST шлют `{"requirements": {...}}`
  напрямую и большинство используют дефолтный `_StubLLMClient(content="Учитывать позитивный
  настрой.")`, который НЕ валидный JSON — после смены body-схемы все они сломаются вдвойне
  (неверная форма запроса + `InvalidVacancyRequirementsResponse` на невалидном stub-контенте).
  Переписать payload на `{"portrait_text": ..., "source_url": ...}` и передавать в `_client(...)`
  `llm_client=_StubLLMClient(content='{"skills": ["python"]}')` (валидный JSON) для всех
  success-кейсов; добавить новый тест с `_StubLLMClient(content="not json")` → 422, `VacancyProfile`
  не создан, фоновый поток скрининга не стартовал (мок/спай на `threading.Thread`).

## Критерии готовности (DoD)

- [ ] успешный запрос с `portrait_text` (без `source_url`) — создаёт версию, `requirements`
      не содержит ключ `source_url`
- [ ] запрос с `source_url` — колонка заполнена, в `requirements` ключа `source_url` нет
- [ ] LLM вернул невалидный JSON → HTTP 422, `VacancyProfile` НЕ создан, фоновый поток
      скрининга НЕ запущен
- [ ] `GET /vacancy-profile/` отдаёт `portrait_text`/`source_url`
- [ ] `uv run pytest` — полный сьют зелёный

## Как проверить

```bash
uv run pytest tests/api/ -v -k vacancy_profile
uv run pytest -q
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-09-10 — `VacancyProfileCreate` теперь принимает `portrait_text`/`source_url`; `create_vacancy_profile`
  вызывает `build_vacancy_requirements` до записи версии, `InvalidVacancyRequirementsResponse` → HTTP 422 без
  создания `VacancyProfile` и без старта фонового потока скрининга; `requirements.pop("source_url", None)`
  перед сохранением. `_serialize_vacancy_profile` отдаёт `portrait_text`/`source_url`. Тесты
  `tests/api/test_vacancy_endpoints.py` переписаны на новую форму body, добавлены тесты на strip
  `source_url` из `requirements` и на 422 при невалидном JSON от LLM (профиль не создан, фоновый
  скрининг не стартовал — проверено через monkeypatch `enqueue_full_screening_for_course`, не через
  спай `threading.Thread.start` — тот ловит и внутренние потоки TestClient). Полный сьют зелёный (263).
