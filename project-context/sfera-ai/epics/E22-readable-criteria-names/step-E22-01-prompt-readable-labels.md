# Шаг E22-01 — читаемые русские названия критериев + версия промпта

**Статус:** DONE
**Слой:** Backend · **Зависит от:** нет (не пересекается с E19/E20/E21 по коду, можно делать
параллельно)
**Перед началом:** прочитай `services/fit_scoring.py::_SYSTEM_PROMPT` (строка ~48, текущая
формулировка про `criteria_scores`), `services/vacancy_portrait.py` (источник сырых
snake_case-ключей вида "последний_опыт" в `vacancy_profile.requirements`, которые модель
сейчас копирует как есть).

## Цель

Ключи `criteria_scores`, которые генерирует LLM, — читаемые русские фразы без `_`
("Последний опыт" вместо "последний_опыт"), а не сырые ключи из JSON-требований вакансии.

## Что сделать

1. Дополнить `_SYSTEM_PROMPT` в `fit_scoring.py`: явно указать — названия критериев в
   `criteria_scores` формулировать по-русски, слова через пробел, с заглавной буквы, без
   символа `_`, по смыслу требования вакансии (не копировать ключ JSON verbatim).
2. Бампнуть `PROMPT_VERSION` с `"fit-scoring-v3"` на `"fit-scoring-v4"` — контракт промпта
   меняется, трекается в `CandidateVacancyAnalysis.prompt_version` для аудита.
3. Проверено ревью-агентом (2026-09-10): `criteria_scores` нигде не используется как
   программный идентификатор (только отображение в `api_read.py`/`ai_card.py`) — переименование
   ключей безопасно, ломать нечего.

## Файлы

- `src/sfera_ai/services/fit_scoring.py` — `_SYSTEM_PROMPT`, `PROMPT_VERSION`.

## Критерии готовности (DoD)

- [x] `PROMPT_VERSION == "fit-scoring-v4"`.
- [x] Промпт явно требует читаемые названия без `_`.
- [x] `uv run pytest` — регрессий нет.

## Как проверить

```bash
uv run pytest tests/services/test_fit_scoring.py
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-09-10: `_SYSTEM_PROMPT` дополнен требованием читаемых русских названий criteria_scores
  (без `_`, не копировать сырой JSON-ключ verbatim). `PROMPT_VERSION` → `fit-scoring-v4`.
  `uv run pytest tests/services/test_fit_scoring.py` — 10 passed.
