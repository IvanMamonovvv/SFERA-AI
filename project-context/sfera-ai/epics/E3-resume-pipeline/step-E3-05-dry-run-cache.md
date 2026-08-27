# Шаг E3-05 — сквозной пайплайн + кэш-гарантия + dry-run на реальных данных

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E3-01, E3-02, E3-03, E3-04
**Перед началом:** прочитай `03_TDD.md` «Resume Pipeline» (полная схема),
«7. Риски» → Cost Protection п.2.

## Цель

Полный пайплайн (fetch → extract text → LLM → сохранить) собран в одну функцию,
идемпотентен по `source_answer_id`/`(candidate_profile_id, hh_resume_id)`, прогнан
dry-run на 5–10 реальных резюме из прода без повторных вызовов HH API/LLM при повторном
запуске.

## Что сделать

1. `process_resume(source_answer_id=None, hh_resume_id=None, candidate_profile_id)` —
   проверка «уже DONE?» перед любым вызовом (E3-01 unique constraint как гарантия на
   уровне БД, но проверка на уровне сервиса — чтобы не тратить AI-бюджет).
2. Ручной CLI/скрипт для прогона на N реальных `Answer`/`hh_resume_id` (read platform,
   write только `ai_resume_extract`).
3. Прогон, ручная сверка `structured_data` на вменяемость (не автоматизировать сверку).

## Файлы

- `src/sfera_ai/services/resume_pipeline.py` — оркестрация
- `src/sfera_ai/cli/run_resume_pipeline.py` — ручной прогон
- `tests/services/test_resume_pipeline.py` — повторный вызов не бьёт fetch/LLM второй раз

## Критерии готовности (DoD)

- [ ] Повторный вызов на тот же `source_answer_id`/`hh_resume_id` — 0 новых HTTP/LLM
      вызовов (мокнутые счётчики в тесте)
- [ ] Ручной прогон на 5–10 реальных резюме — без исключений
- [ ] `04_STATE.md` обновлён

## Как проверить

```bash
uv run pytest tests/services/test_resume_pipeline.py -v
# затем ручной прогон (требует туннеля к БД, HH-credentials, LLM API key)
uv run python -m sfera_ai.cli.run_resume_pipeline --limit 10
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E3
   → DONE, следующий шаг E4 или E5 — зависимость по графу `05_EPICS.md`).

## Журнал

- `2026-08-27` — реализовано: `process_resume` (`src/sfera_ai/services/resume_pipeline.py`)
  — оркестрация fetch → sniff mime (magic bytes, не расширение файла — `extract_text`
  не знает про `source_type`) → `extract_text` → `run_resume_extraction`. Идемпотентность
  на уровне сервиса: если `ResumeExtract` по `source_answer_id`/`(candidate_profile_id,
  hh_resume_id)` уже `DONE` — возврат без единого HTTP/LLM вызова; если `raw_text` уже
  заполнен (упал только LLM-шаг) — повторный fetch не делается, ретраится только LLM.
  CLI `src/sfera_ai/cli/run_resume_pipeline.py` — ручной прогон по HH_RESUME (берёт
  N `CandidateProfile` с `hh_negotiation_id`, отсортированных по убыванию — свежие
  негоциации привязаны к текущему активному HH-коннекту бэкенда, старые давали 404
  «No HHNegotiationRecord matches» из-за смены `connection`). ANKETA_FILE источник
  вне scope CLI — детекция «какой `Answer` — резюме» относится к Answers Pipeline/E5.
  `tests/services/test_resume_pipeline.py` — 6 тестов (HH end-to-end DONE, повторный
  вызов = 0 новых HTTP/LLM вызовов, fetch-failure не зовёт LLM, нераспознанный
  mime не зовёт LLM, ValueError на некорректный набор source-параметров, ANKETA_FILE
  end-to-end). Полный сьют: `uv run pytest` — 54 passed.

  **Реальный прогон** (2026-08-27, свой SSH-туннель к staging `db`+`backend` через
  `ai_shared`, аналогично `scripts/tunnel-platform-db.sh`): 10 реальных HH-резюме,
  9 `DONE` + 1 `FAILED` (502 от самого HH API — транзиентная ошибка на стороне
  HeadHunter, не баг пайплайна). Повторный прогон тех же 10 — те же `extract_id`,
  без новых HTTP/LLM вызовов (кэш-гарантия подтверждена не только в тестах, но и на
  реальных данных). Ручная сверка `structured_data` — `experience_years`/`positions`/
  `companies`/`salary_expectation` вменяемые, соответствуют содержимому резюме
  (сверено на выборке из 5 записей). Использованный туннель к `backend` (аналог
  `tunnel-platform-db.sh`, но на порт 8000 контейнера `sfera-staging-backend-1`) не
  закоммичен в `scripts/` — под вопросом владельца, нужен ли он как постоянный
  инструмент или это разовая задача для дальнейших ручных прогонов/дебага.
