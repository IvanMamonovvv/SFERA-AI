# Шаг E10-02 — портрет кандидата + ссылка на вакансию → VacancyProfile

**Статус:** DONE
**Слой:** Backend (CLI) · **Зависит от:** E1
**Перед началом:** прочитай `services/feedback_interpretation.py` (образец простого
синхронного LLM-синтеза) и `services/vacancy_profile.py` (`create_vacancy_profile_version`,
переиспользуется как есть).

## Контекст / зачем

Владелец хочет присылать текстовый портрет идеального кандидата и, опционально,
ссылку на открытый источник вакансии (например hh.ru), из которых нужно собрать
`VacancyProfile.requirements` — при необходимости менять/дополнять портрет новой
версией. Согласовано в диалоге 2026-08-31 (см. `04_STATE.md`).

## Цель

Новая подкоманда `vacancy-profile create-from-portrait`: текст портрета (+ опционально
URL публичного описания вакансии) одним LLM-вызовом превращаются в структурированный
`requirements`, дальше — обычная версия `VacancyProfile` через уже существующий сервис.

## Что сделать

1. Новая зависимость `beautifulsoup4` (`uv add`) — HTML → читаемый текст (без
   тегов/скриптов/меню) перед LLM-вызовом, экономия токенов и точность.
2. `build_vacancy_requirements(portrait_text, source_url, *, llm_client) -> dict` —
   новый сервис (`src/sfera_ai/services/vacancy_portrait.py`). Если `source_url` дан —
   скачать (httpx), вычистить (`BeautifulSoup.get_text`), обрезать до разумной длины
   (~8000 символов, чтобы не раздувать промпт); ошибка скачивания (таймаут/404/
   бот-блок) — залогировать и продолжить только по портрету, не падать (согласовано
   2026-08-31). Один LLM-вызов (по образцу `feedback_interpretation.py`,
   `response_format={"type": "json_object"}` как в `resume_extraction.py`) — портрет +
   (если есть) текст вакансии → структурированный JSON `requirements`; `source_url`
   (если был) кладётся внутрь этого JSON как ключ `source_url` — без миграции схемы
   `VacancyProfile` (поле `requirements` уже свободный JSON, `fit_scoring.py` просто
   прокидывает его в промпт как есть).
3. Невалидный JSON от LLM — не создавать `VacancyProfile`, явная ошибка (как
   `run_resume_extraction`/`InvalidFitScoringResponse` — не писать частичный результат).
4. Подкоманда `create-from-portrait` в `cli/vacancy_profile.py` — `--course-id`,
   `--portrait-text`/`--portrait-file` (@file, как `--requirements-json` в `create`),
   `--source-url` (опционально) → `build_vacancy_requirements` →
   `create_vacancy_profile_version` (уже триггерит `enqueue_fit_recalc_for_course`,
   ничего дополнительно делать не нужно).

## Файлы

- `src/sfera_ai/services/vacancy_portrait.py` — новый сервис
- `src/sfera_ai/cli/vacancy_profile.py` — подкоманда `create-from-portrait`
- `pyproject.toml`/`uv.lock` — `beautifulsoup4`
- `tests/services/test_vacancy_portrait.py` — `build_vacancy_requirements` (мок LLM/HTTP)

## Критерии готовности (DoD)

- [x] `build_vacancy_requirements` — с URL и без; ошибка скачивания URL не блокирует
      сборку по портрету
- [x] невалидный JSON от LLM-синтеза требований → явная ошибка, `VacancyProfile` не создан
- [x] `source_url` (если был передан) присутствует в итоговом `requirements`
- [x] `uv run pytest` — полный сьют зелёный, регрессий нет

## Как проверить

```bash
uv run pytest tests/services/test_vacancy_portrait.py -v
uv run pytest -q
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-09-01` — **реальное использование на проде**: владелец прислал ссылку на курс
  (`https://sphera-link.online/course/123be98a949d4d4f926b2e0518b22d3c?slug=sfera`) и
  текст портрета («Идеальный кандидат — менеджер по корпоративным продажам», B2B-хантер,
  холодные звонки, работа без CRM). `course_id=39` резолвлен по UUID из ссылки через
  `resolve_course_id` (`services/api_read.py`). `create-from-portrait` создал
  `VacancyProfile` id=4, v1, `is_current=true` для `course_id=39` — LLM корректно разобрал
  портрет на структурированные `requirements` (experience/skills/personal_qualities/
  work_conditions/interview_requirements), `source_url` сохранён в JSON. Триггер
  пересчёта fit по курсу (E7-04) отработал автоматически. Использован дальше в
  `step-E10-01-full-course-screening.md` (реальный прогон того же дня).
- `2026-08-31` — реализовано: зависимость `beautifulsoup4` (`uv add`),
  `build_vacancy_requirements(portrait_text, source_url, *, llm_client)` в новом
  `services/vacancy_portrait.py` — скачивание `source_url` через `httpx.get` (30s
  timeout), `BeautifulSoup.get_text` без script/style тегов, обрезка до 8000 символов;
  ошибка скачивания (таймаут/HTTP-ошибка) логируется и не блокирует сборку — продолжает
  только по портрету. Один LLM-вызов (`response_format={"type": "json_object"}`, по
  образцу `resume_extraction.py`), невалидный JSON или не-объект → явная
  `InvalidVacancyRequirementsResponse` ДО создания `VacancyProfile` (по паттерну
  `InvalidFitScoringResponse`). `source_url` (если был) добавляется в итоговый JSON
  ключом `source_url`. Подкоманда `create-from-portrait` в `cli/vacancy_profile.py` —
  `--course-id`, ровно один из `--portrait-text`/`--portrait-file` (@file), опционально
  `--source-url`/`--notes`, переиспользует `create_vacancy_profile_version` как есть.
  Тесты — `tests/services/test_vacancy_portrait.py` (5: без URL, с URL+source_url в
  результате, ошибка скачивания URL не блокирует, невалидный JSON, JSON-не-объект).
  Полный сьют `uv run pytest` — 183 passed, регрессий нет.
