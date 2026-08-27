# Шаг E3-04 — LLM structured extraction

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E3-03
**Перед началом:** прочитай `03_TDD.md` раздел «AI Pipeline — какие вызовы и когда»
(единый клиент `ai_analysis/providers.py`), раздел «7. Риски и решения» → Cost
Protection.

## Цель

`raw_text` резюме превращается в `structured_data` (опыт/должности/компании/зарплатные
ожидания) через LLM, ровно один вызов на `ResumeExtract`.

## Что сделать

1. Тонкий провайдер-клиент (OpenRouter) с логированием `provider`/`model`/
   `prompt_version`/токенов/latency — общий модуль, переиспользуется всеми будущими
   LLM-вызовами (E6, E7).
2. Промпт + JSON-схема для `structured_data`.
3. Сервис `run_resume_extraction(extract_id)`: PENDING → вызов LLM → DONE +
   `structured_data`+`processed_at`, или FAILED + `error` при невалидном JSON
   (try/except вокруг парсинга, не пишет частичный результат).

## Файлы

- `src/sfera_ai/providers.py` — общий LLM-клиент (создаётся здесь, переиспользуется E6/E7)
- `src/sfera_ai/services/resume_extraction.py`
- `tests/services/test_resume_extraction.py` — мокнутый LLM-ответ (валидный/невалидный
  JSON)

## Критерии готовности (DoD)

- [x] Валидный ответ LLM → `DONE` + заполненный `structured_data`
- [x] Невалидный JSON → `FAILED`, `error` содержит обрезанный сырой ответ, не роняет
      процесс
- [x] `provider`/`model`/`prompt_version`/токены/latency пишутся на каждый вызов

## Как проверить

```bash
uv run pytest tests/services/test_resume_extraction.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — `src/sfera_ai/providers.py` (`OpenRouterClient`, общий на E6/E7),
  `src/sfera_ai/services/resume_extraction.py` (`run_resume_extraction`), тесты
  TDD-циклом (`tests/test_providers.py`, `tests/services/test_resume_extraction.py`,
  48/48 зелёные). `provider`/`model`/`prompt_version` пишутся в `ResumeExtract`; токены/
  latency логируются на каждый вызов (в модели `ResumeExtract` нет колонок под них —
  в отличие от `CandidateVacancyAnalysis`, `03_TDD.md` раздел 2). Добавлен
  `openrouter_api_key`/`openrouter_base_url` в `config.py`.
