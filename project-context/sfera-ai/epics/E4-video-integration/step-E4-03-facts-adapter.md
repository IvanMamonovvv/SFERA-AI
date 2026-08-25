# Шаг E4-03 — адаптер видео-фактов для сборки профиля

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E4-02
**Перед началом:** прочитай `03_TDD.md` «Candidate Profile — как строится и
обновляется» (таблица источников).

## Цель

Готовый `TranscriptionJob.summary_text` превращается в факт-объект в формате, который E6
(сборка `CandidateProfile.facts`) сможет подмешать напрямую — без LLM-вызова (видео уже
дало текстовый саммари, второй вызов не нужен).

## Что сделать

1. Функция `video_facts_from_transcript(job) -> list[dict]` — формат факта как в
   `03_TDD.md`: `{"key", "value", "confidence", "evidence": [{"source_type": "VIDEO",
   "source_id": answer_id, "excerpt": ...}]}`.
2. Ограничение по `03_TDD.md`: полагаться только на `transcript_text`/`summary_text`, не на
   сам видеофайл (удаляется через 30 дней).

## Файлы

- `src/sfera_ai/services/video_facts.py` — расширение (та же функция из E4-02 + адаптер)
- `tests/services/test_video_facts.py`

## Критерии готовности (DoD)

- [ ] Факт-объекты соответствуют схеме `03_TDD.md`
- [ ] Нет обращения к видеофайлу/S3, только к текстовым полям `TranscriptionJob`

## Как проверить

```bash
uv run pytest tests/services/test_video_facts.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E4
   → DONE).

## Журнал

- `YYYY-MM-DD` — <что сделано>.
