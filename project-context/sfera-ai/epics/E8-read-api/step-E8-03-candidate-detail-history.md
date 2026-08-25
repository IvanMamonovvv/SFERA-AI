# Шаг E8-03 — карточка кандидата + история версий

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E8-02

## Цель

`GET .../candidates/{id}/` и `GET .../candidates/{id}/history/` отдают полную карточку
и историю версий по контракту TDD.

## Что сделать

1. `candidates/{id}/` — текущий `CandidateVacancyAnalysis` + `CandidateProfile.facts` +
   evidence + сжатая история версий (id, fit_score, analyzed_at, что изменилось).
2. `candidates/{id}/history/` — полный список версий с diff `input_snapshot` между
   соседними версиями (объясняет «52→87»).
3. 404 на несуществующий `candidate_profile_id`/`course_uuid`.

## Файлы

- `src/sfera_ai/api/routes/candidates.py` — расширение
- `src/sfera_ai/services/api_read.py` — расширение
- `tests/api/test_candidate_detail.py`

## Критерии готовности (DoD)

- [ ] Оба эндпоинта покрыты тестами
- [ ] Diff между версиями в `history/` человекочитаем (не сырой JSON-дамп двух
      снепшотов без пояснения)

## Как проверить

```bash
uv run pytest tests/api/test_candidate_detail.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
