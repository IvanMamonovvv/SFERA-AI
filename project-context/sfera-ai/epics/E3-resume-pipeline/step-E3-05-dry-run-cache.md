# Шаг E3-05 — сквозной пайплайн + кэш-гарантия + dry-run на реальных данных

**Статус:** TODO
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

- `YYYY-MM-DD` — <что сделано, результат прогона на реальных данных>.
