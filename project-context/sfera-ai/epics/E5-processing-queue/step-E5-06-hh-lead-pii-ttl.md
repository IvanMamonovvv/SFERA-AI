# Шаг E5-06 — TTL сырого PII резюме для неконвертировавшихся HH-лидов

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E5-05, E3-01 (`ResumeExtract` модель)
**Перед началом:** прочитай `02_CONTEXT.md` «Решения владельца» (2026-08-26, TTL на
`raw_text` HH-лидов) и `03_TDD.md`, раздел `ResumeExtract`. Контекст: платформа не может
удалить `HHNegotiationRecord`, который никогда не конвертировался в `Application`
(152-ФЗ `hard_delete_user_data` требует существующего `User`) — AI-сервис не должен
бессрочно хранить свою копию сырого текста резюме для этой категории.

## Цель

Отдельный cron (раз в сутки) стирает `ResumeExtract.raw_text`/`structured_data` старше
N дней (`RESUME_PII_TTL_DAYS`, конфиг) для профилей, которые всё ещё `hh_negotiation`-only
(`application_id IS NULL`) — то есть лид не конвертировался в платформенного кандидата.
Структурированные факты, уже перенесённые в `CandidateProfile.facts`, не трогаются —
удаляется только сырой источник-кэш.

## Что сделать

1. Конфиг `RESUME_PII_TTL_DAYS` (default 90 — согласовать точное число с владельцем
   перед прод-запуском, значение-заглушка на этапе разработки).
2. Функция `purge_expired_hh_lead_resumes(ttl_days)`:
   ```python
   ResumeExtract.objects... .filter(
       candidate_profile__application_id__is_(None),
       processed_at < now() - timedelta(days=ttl_days),
   ).update(raw_text="", structured_data={})
   ```
   (SQLAlchemy-эквивалент — `UPDATE ... WHERE ...`, не `DELETE` строки: `ResumeExtract`
   остаётся как запись о факте обработки, `status=DONE` не меняется, только PII-поля
   очищаются — иначе change detection на следующем тике увидит "источника нет" и
   попробует распарсить резюме заново).
3. Если после TTL лид всё же конвертируется в `Application` (`HHNegotiationRecord.application`
   становится не-null) — `raw_text` уже пуст, повторный парсинг не запускается
   автоматически (кэш считается `DONE`). Это осознанный компромисс: `CandidateProfile.facts`
   уже содержит факты, извлечённые до очистки, `data_completeness` не деградирует;
   восстановление сырого текста — только через `MANUAL`/`BACKFILL` re-trigger, если
   реально понадобится.
4. Регистрация как отдельный периодический job в `BackgroundScheduler` (интервал сутки).

## Файлы

- `src/sfera_ai/services/pii_retention.py` — создать
- `tests/services/test_pii_retention.py` — тест (просроченный hh-lead-only профиль →
  `raw_text` пуст, факты остаются; профиль с `application_id` заполненным — не трогается,
  даже если старше TTL; свежий hh-lead-only профиль — не трогается)

## Критерии готовности (DoD)

- [ ] `raw_text`/`structured_data` очищены для `hh_negotiation`-only профилей старше TTL
- [ ] Профили с заполненным `application_id` (конвертировавшиеся) не затрагиваются
      независимо от возраста
- [ ] `CandidateProfile.facts` не изменяется, `ResumeExtract.status` остаётся `DONE`

## Как проверить

```bash
uv run pytest tests/services/test_pii_retention.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
