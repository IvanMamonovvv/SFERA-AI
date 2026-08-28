# Шаг E8-03 — карточка кандидата + история версий

**Статус:** DONE
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

- [x] Оба эндпоинта покрыты тестами
- [x] Diff между версиями в `history/` человекочитаем (не сырой JSON-дамп двух
      снепшотов без пояснения)

## Как проверить

```bash
uv run pytest tests/api/test_candidate_detail.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-28` — выполнено. `src/sfera_ai/services/api_read.py`:
  `get_candidate_detail(session, course_id, candidate_profile_id)` — все версии
  `CandidateVacancyAnalysis` для candidate_profile_id+course_id, если пусто → `None` (404
  в роуте). `current` — версия с `is_current=True` (fallback на последнюю по `version`,
  на случай гонки), полный набор полей включая `evidence`/`strengths`/`risks`/`gaps` и
  т.д. `facts` — `CandidateProfile.facts` напрямую. `history` — сжато: `id`, `version`,
  `fit_score`, `analyzed_at`, `changed` (список имён полей `fit_score`/`confidence`/
  `data_completeness`/`recommendation`, изменившихся относительно предыдущей версии;
  первая версия — `changed=[]`).
  `get_candidate_history(session, course_id, candidate_profile_id)` — полный список
  версий с `input_snapshot_diff` (человекочитаемый: только ключи, у которых значение
  реально изменилось, `{key: {old, new}}`, вычисляется хелпером `_snapshot_diff`; первая
  версия — `{}`, сравнивать не с чем). Оба сервиса переиспользуют одну query (order by
  `version` asc) — без лишних round-trip'ов к БД.
  Роуты — `src/sfera_ai/api/routes/candidates.py`:
  `GET /candidates/{candidate_profile_id}/`, `GET /candidates/{candidate_profile_id}/history/`,
  404 при неизвестном `course_uuid` (уже было, `_resolve_course_or_404`) и при
  candidate_profile_id без единой версии анализа в этом course (сервис вернул `None`).
  Тесты — `tests/api/test_candidate_detail.py` (5: карточка с current+facts+сжатой
  историей, 404 неизвестный кандидат, 404 неизвестный course, history с читаемым diff,
  404 history неизвестный кандидат). `uv run pytest` — 145 passed, регрессий нет.
