# Шаг E6-03 — LLM Fit-вызов

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E6-01, E6-02, E7 (частично — активные `VacancyMemory`,
если E7 ещё не готов, подмешивать пустой список)
**Перед началом:** прочитай `03_TDD.md` «AI Pipeline» → Fit scoring, «Versioning —
сводно» → `CandidateVacancyAnalysis`.

## Цель

`facts + requirements + активные VacancyMemory → fit_score + evidence + recommendation`
— реальный (не dry-run) LLM-вызов, результат сохраняется как новая иммутабельная версия
`CandidateVacancyAnalysis`, `is_current` переключается транзакцией.

## Что сделать

1. Промпт-сборка: `CandidateProfile.facts` + `VacancyProfile.requirements` (`is_current`)
   + активные `VacancyMemory.rule_text` этого `course`.
2. Вызов через общий `providers.py` (из E3-04) — сохранение
   `provider`/`model`/`prompt_version`/токенов/`cost_estimate`/`latency_ms`.
3. `input_snapshot` — копия `sources_snapshot` + `vacancy_profile_id` + `memory_ids[]`
   на момент расчёта (нужно для «почему скор изменился» диффа).
4. Транзакция: создать новую версию, снять `is_current` со старой, поставить на новой —
   одна транзакция, не два отдельных коммита.
5. Невалидный JSON от LLM → не пишет частичную версию, ошибка наверх для
   `AIProcessingJob.FAILED` (обработка ошибки — уровень E5, здесь только пробросить).

## Файлы

- `src/sfera_ai/services/fit_scoring.py`
- `tests/services/test_fit_scoring.py` — мокнутый LLM-ответ

## Критерии готовности (DoD)

- [ ] Новая версия создаётся, старая `is_current` снимается — в одной транзакции
- [ ] `input_snapshot` содержит все три компонента (профиль/вакансия/memory)
- [ ] Невалидный ответ LLM не создаёт запись в БД

## Как проверить

```bash
uv run pytest tests/services/test_fit_scoring.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
