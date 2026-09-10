# Шаг E17-04 — новые факты резюме: возраст и отрасль

**Статус:** DONE (код готов, ручная проверка на реальном резюме — не выполнена)
**Слой:** Backend · **Зависит от:** E17-01..03 (DONE)
**Перед началом:** прочитай `src/sfera_ai/services/resume_extraction.py`,
`src/sfera_ai/services/candidate_facts.py`. Контекст — решение владельца 2026-09-10
(сравнение с эталонной карточкой РТХ, см. `step-E17-06-rtx-visual-style-match.md`):
в шапке карточки нужны возраст и отрасль последнего места работы кандидата — этих
полей сейчас нет ни в извлечении резюме, ни в `facts`.

## Цель

`CandidateProfile.facts` после ре-экстракции резюме кандидата содержит ключи `age`
(число) и `industry` (строка) с приоритетом источника наравне с остальными
резюме-фактами.

## Что сделать

1. `resume_extraction.py`, `_SYSTEM_PROMPT` (строки 12-20) — добавить в список полей
   JSON-ответа: `age` (число или null, возраст кандидата), `industry` (строка или
   null — короткая метка сферы/индустрии последнего места работы, напр.
   "Химическое сырьё", "Техническая номенклатура").
2. `resume_extraction.py`, `PROMPT_VERSION` (строка 9) — бампнуть
   `"resume-extract-v1"` → `"resume-extract-v2"` (меняется контракт ответа LLM).
3. `candidate_facts.py`, `_RESUME_FACT_KEYS` (строка 26) — добавить `"age"`,
   `"industry"` в кортеж, чтобы `_resume_facts()` прокидывал их в `facts`.

## Файлы

- `src/sfera_ai/services/resume_extraction.py` — промпт + версия
- `src/sfera_ai/services/candidate_facts.py` — `_RESUME_FACT_KEYS`

## Критерии готовности (DoD)

- [ ] На реальном резюме (напр. `Downloads/candidate_2964/`) после ре-экстракции
      `ResumeExtract.structured_data` содержит `age`/`industry`
- [ ] `CandidateProfile.facts` содержит факты с `key="age"` и `key="industry"`
- [ ] Существующие тесты `resume_extraction`/`candidate_facts` зелёные

## Как проверить

```bash
uv run pytest tests/ -k "resume_extraction or candidate_facts"
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-09-10` — шаг создан (выделен из объединённого плана по итогам обсуждения
  с владельцем, разбивка на 3 узких шага per конвенция проекта).
- `2026-09-10` — реализовано: `_SYSTEM_PROMPT` дополнен полями `age`/`industry`,
  `PROMPT_VERSION` → `resume-extract-v2`, `_RESUME_FACT_KEYS` дополнен `"age"`,
  `"industry"`. Тесты `resume_extraction`/`candidate_facts` зелёные (18 passed).
  Ручная проверка на реальном резюме (`Downloads/candidate_2964/`) не проводилась —
  требует ре-экстракции через реальный LLM-вызов.
