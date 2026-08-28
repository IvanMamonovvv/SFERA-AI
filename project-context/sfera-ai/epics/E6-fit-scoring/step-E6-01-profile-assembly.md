# Шаг E6-01 — сборка `CandidateProfile.facts`

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E2, E3 (резюме-факты), E4 (видео-факты)
**Перед началом:** прочитай `03_TDD.md` «Candidate Profile — как строится и
обновляется» (таблица источников, `data_completeness`).

## Цель

По `CandidateProfile` собирается/дополняется `facts` из всех доступных источников
(HH resume / анкетное резюме / ответы / видео), инкрементально — не полная пересборка,
`data_completeness` считается по количеству реально присутствующих источников.

## Что сделать

1. `build_or_update_candidate_facts(profile)` — читает `sources_snapshot`, сравнивает с
   текущим состоянием (переиспользует E5-02 `needs_profile_rebuild` как триггер),
   дополняет `facts` только новым.
2. Батч новых `Answer` → LLM-вызов (не по одному) — прямые факты из анкеты
   (`03_TDD.md` «Answers Pipeline»).
3. Подмешивание готовых `ResumeExtract.structured_data` и видео-фактов (E4-03) без
   повторного LLM-вызова на них.
4. Пересчёт `data_completeness`, инкремент `version`, новый `sources_snapshot`.

## Файлы

- `src/sfera_ai/services/candidate_facts.py`
- `tests/services/test_candidate_facts.py`

## Критерии готовности (DoD)

- [ ] Повторный вызов без новых источников — `facts`/`version` не меняются
- [ ] Новый источник — только дельта добавляется, старые факты не переписываются
- [ ] `data_completeness` считается корректно на всех комбинациях источников

## Как проверить

```bash
uv run pytest tests/services/test_candidate_facts.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — `build_or_update_candidate_facts(session, platform_base, llm_client, profile)`
  (`src/sfera_ai/services/candidate_facts.py`). Триггер — вынесенный из `needs_profile_rebuild`
  `compute_current_sources_snapshot` (`change_detection.py`, рефакторинг без изменения
  поведения — 3 старых теста прошли без правок). Батч новых `Answer.text` → один LLM-вызов
  (JSON `{"facts":[...]}`); `ResumeExtract.structured_data` (оба `source_type`) и видео
  (`testchecks_transcriptionjob` по `answer_id` кандидата) подмешиваются без LLM. Дедуп
  фактов по `(key, evidence.source_type, evidence.source_id)` — старые не переписываются.
  `data_completeness`: 0 источников → `MINIMAL`, 1-2 → `PARTIAL`, 3-4 → `FULL` (решение
  принято в рамках шага — точных порогов в TDD не было). Новая таблица в reflection:
  `CANDIDATE_FACTS_TABLES` (`platform_db.py`) = `CHANGE_DETECTION_TABLES` +
  `testchecks_transcriptionjob`. Вне scope шага (не реализовано здесь): создание
  `ResumeExtract` для `ANKETA_FILE`-ответа (детекция «какой Answer — резюме» и вызов
  `process_resume`) — по DoD шага подмешиваются только уже готовые `DONE`-записи;
  переносится в очередь (`E6-04`) или отдельный шаг. Тесты:
  `tests/services/test_candidate_facts.py` (6, sqlite in-memory) — все GREEN. Полный
  сьют `uv run pytest` — 88 passed.
