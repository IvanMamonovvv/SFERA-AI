# Шаг E6-03 — LLM Fit-вызов

**Статус:** DONE
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

- [x] Новая версия создаётся, старая `is_current` снимается — в одной транзакции
- [x] `input_snapshot` содержит все три компонента (профиль/вакансия/memory)
- [x] Невалидный ответ LLM не создаёт запись в БД

## Как проверить

```bash
uv run pytest tests/services/test_fit_scoring.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — реализовано: `src/sfera_ai/services/fit_scoring.py` —
  `run_fit_scoring(session, candidate_profile, vacancy_profile, llm_client, memory_ids=None,
  memory_rule_texts=None)`. `VacancyMemory` (E7) ещё не реализована — вызывающий код передаёт
  пустые списки, сигнатура готова принять их без изменений после E7. Промпт собирается из
  `CandidateProfile.facts` + `VacancyProfile.requirements` + `memory_rule_texts`. Вызов через
  `OpenRouterClient.complete` (`providers.py`, из E3-04), `response_format=json_object`.
  Валидация ответа LLM (`_parse_and_validate`): не просто `json.loads`, но и проверка
  допустимых значений `confidence`/`recommendation` (choices из TDD), диапазонов
  `fit_score`/`data_completeness`, типов списковых/dict-полей — любое нарушение бросает
  `InvalidFitScoringResponse` ДО какой-либо записи в БД (session.add/commit только после
  успешной валидации). `LLMProviderError` не перехватывается — пробрасывается вызывающему
  коду как есть (уровень retry/FAILED — зона ответственности E5). Транзакция версии:
  паттерн скопирован из `services/vacancy_profile.py` — снять `is_current` со старой версии,
  `session.flush()` (важно: до insert новой, иначе partial index на миг видит две
  `is_current=True`), затем добавить новую версию и один `session.commit()`. `input_snapshot`
  = `{**candidate_profile.sources_snapshot, "vacancy_profile_id", "memory_ids"}` — все три
  компонента, как того требует DoD. `cost_estimate` оставлен `None` — в кодовой базе нет
  прецедента/тарифной формулы расчёта стоимости по токенам, поле в модели уже есть, посчитать
  можно будет позже, когда появится согласованный прайс по моделям (TODO, не блокирует шаг).
  Тесты — `tests/services/test_fit_scoring.py` (6): первая версия is_current, input_snapshot
  содержит все три компонента, вторая версия снимает is_current с первой в одной транзакции,
  невалидный JSON бросает исключение и не пишет строку, невалидное значение enum-поля
  (`confidence`) — то же самое, ошибка провайдера (`LLMProviderError`) пробрасывается и не
  пишет строку. Полный сьют `uv run pytest` — 107 passed, регрессий нет.
