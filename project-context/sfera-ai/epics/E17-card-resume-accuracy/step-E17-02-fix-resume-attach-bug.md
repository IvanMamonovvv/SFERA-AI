# Шаг E17-02 — Проверить/починить невложение резюме при `status=DONE`

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E9-02 (`services/export/files.py`,
`services/resume_fetch.py`)
**Перед началом:** прочитай `04_STATE.md` запись `2026-09-06` (кейс кандидата
Петрусевич Е.Д., `candidate_profile_id=2398` — резюме не приложилось в ZIP при
`ResumeExtract.status=DONE`), `04_STATE.md` запись `2026-09-09` («новое» — фикс
мультитенантности `company_slug`, коммит `0af0089`), `src/sfera_ai/services/resume_fetch.py`
(`fetch_resume_bytes`, `_fetch_hh_resume`, `_fetch_anketa_file`),
`src/sfera_ai/services/export/files.py` (`_resume_file`).

## Контекст — вероятно уже исправлено

Кейс Петрусевич зафиксирован **2026-09-06**. `_fetch_hh_resume` (`resume_fetch.py:28`)
резолвит `company_slug` через `resolve_company_slug_for_hh_negotiation` и вызывает
`hh_client.get_resume_pdf(hh_negotiation_id, company_slug)`. Запись `04_STATE.md`
**2026-09-09** описывает найденный и исправленный баг: `HHClient` раньше резолвил
`company_slug` из ОДНОГО глобального `.env` вместо per-company — платформа
мультитенантна, для компаний, отличных от той, что была захардкожена, резюме не
подтягивались бы (404/чужие данные), молча. Это по симптомам совпадает с кейсом
Петрусевич (резюме `status=DONE` — экстракция когда-то прошла, но повторное
скачивание при экспорте зип-архива падает). Не подтверждено: у Петрусевич резюме
именно `source_type=HH_RESUME` (не `ANKETA_FILE`) и именно из-за этого конкретного
бага — не расследовано в моменте 2026-09-06.

## Цель

Понять, воспроизводится ли ещё невложение резюме в архив при `ResumeExtract.status=
DONE` — если фикс `0af0089` его уже закрыл, шаг закрывается без изменений кода
(регрессионный тест на всякий случай не помешает); если нет — найти и исправить
реальную причину.

## Что сделать

1. Проверить `source_type` у `ResumeExtract` кандидата 2398 (Петрусевич) на реальной
   БД (staging/прод, через `tunnel-platform-db.sh`, явное разрешение владельца на
   каждый SSH/DB-доступ) — HH_RESUME или ANKETA_FILE.
2. Повторить экспорт (или напрямую `collect_export_files`) для этого кандидата на
   актуальном коде (после `0af0089`) — воспроизводится ли ещё «resume: недоступно
   (резюме не найдено)» в `manifest.txt`.
3. Если не воспроизводится — считать закрытым фиксом мультитенантности, добавить
   регрессионный тест на путь `_fetch_hh_resume` с несколькими компаниями (если ещё
   не покрыт тестами `0af0089`), закрыть шаг.
4. Если воспроизводится — отладить конкретную причину (`ResumeFetchError` пишет
   `extract.error` — прочитать текст ошибки на реальной записи), поправить код,
   тест на конкретный сценарий.

## Файлы

- `src/sfera_ai/services/resume_fetch.py` — если баг ещё жив
- `tests/services/test_resume_fetch.py` / `tests/services/test_export_files.py` —
  регрессионный тест

## Критерии готовности (DoD)

- [ ] Причина невложения резюме у кандидата 2398 установлена (подтверждён баг
      `company_slug`, либо найдена другая причина)
- [ ] Если код менялся — регрессионный тест воспроизводит старое поведение и
      проверяет исправление
- [ ] `uv run pytest` — полный сьют зелёный

## Как проверить

```bash
uv run pytest tests/services/test_resume_fetch.py tests/services/test_export_files.py -v
# + при необходимости живая проверка через tunnel-platform-db.sh на candidate_profile_id=2398
#   (явное разрешение владельца на каждый SSH/DB-доступ)
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг).

## Журнал

- **2026-09-10.** Реальный статус на staging (`ssh sfera`, `sfera-staging-db-1`, разрешение
  владельца на каждый доступ): `ai_resume_extract` кандидата 2398, `source_type=HH_RESUME`,
  `status=FAILED`, `error="backend request failed: Server disconnected without sending a
  response."` — не `DONE`, как предполагал шаг. Фикс мультитенантности `company_slug`
  (`0af0089`) здесь ни при чём — не company_slug ошибка.
  Найдена реальная причина: `fetch_resume_bytes` (`resume_fetch.py`) при ЛЮБОЙ ошибке
  безусловно переводит `extract.status="FAILED"` и коммитит. Эта же функция
  использовалась в двух разных местах — (1) `resume_pipeline.py` при первичной
  экстракции (легитимно: если байты резюме не скачались, экстракция и должна упасть) и
  (2) `export/files.py::_resume_file` при СБОРКЕ ZIP-АРХИВА, где `extract` уже выбран
  строго с `status=="DONE"` и файл перескачивается только чтобы приложить оригинал.
  Временный сетевой сбой при (2) — как у Петрусевич — навсегда портил уже валидный
  `DONE` на `FAILED`, что ломало не только вложение файла в архив, но и
  `resume_status`/`candidate_facts`/скоринг при последующих запусках (эти места читают
  `ResumeExtract.status == "DONE"`).
  Исправлено: `resume_fetch.py` — dispatch-логика вынесена в `_dispatch_fetch`;
  `fetch_resume_bytes` (мутирует `status`) оставлена только для пайплайна экстракции;
  добавлена `fetch_resume_bytes_readonly` (НЕ мутирует `status`/`error` при ошибке) —
  используется в `export/files.py::_resume_file`. Регрессионные тесты:
  `test_resume_fetch.py::test_fetch_resume_bytes_readonly_error_does_not_mutate_status`,
  `test_export_files.py::test_resume_refetch_failure_at_export_does_not_corrupt_done_status`.
  `uv run pytest` — 213 passed (1 известный флаки-тест `test_vacancy_endpoints.py`
  на фоновых джобах не связан, проходит отдельно).
  Не сделано в рамках этого шага: восстановление статуса кандидата 2398 (сейчас
  `FAILED` в БД) — отдельное решение владельца (ре-экстракция задним числом или
  оставить как есть, влияет на скоринг конкретного кандидата).
