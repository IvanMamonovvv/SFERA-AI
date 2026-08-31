# Шаг E9-02 — оригинал резюме + видеовизитка

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E9-01
**Перед началом:** прочитай `03_TDD.md» «Future Export» (переиспользование
`collect_candidate_archive_entries`-подобной логики — **своя реализация**, чужой код
backend'а не импортируется, разные репозитории).

## Цель

По кандидату собираются: оригинальный файл резюме (`Answer.file`/HH PDF) и
видеовизитка (`Answer.file` video S3 key) — тем же паттерном, что архивный сервис
backend'а, но собственным кодом.

## Что сделать

1. `collect_export_files(candidate_profile_id) -> dict` — читает через reflection
   нужные `Answer.file`/HH resume ссылку, собственный S3-клиент (уже есть с E3-02) для
   скачивания.
2. Обработка отсутствующих файлов (видео удалено через 30 дней — `03_TDD.md`
   ограничение) — export не падает, помечает файл как недоступный.

## Файлы

- `src/sfera_ai/services/export/files.py`
- `tests/services/test_export_files.py`

## Критерии готовности (DoD)

- [ ] Наличие обоих файлов — оба собираются
- [ ] Отсутствие видео (истёк срок) — export продолжается без него, явный маркер в
      результате

## Как проверить

```bash
uv run pytest tests/services/test_export_files.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-28 — `collect_export_files(session, platform_base, candidate_profile_id, *, hh_client,
  s3_client, s3_bucket) -> dict` в `src/sfera_ai/services/export/files.py`. Резюме — переиспользует
  готовый `fetch_resume_bytes` (E3-02) на последнем `ResumeExtract(status="DONE")` кандидата.
  Видео — join `testchecks_answer` → `testchecks_testattempt` → `testchecks_transcriptionjob`
  (`status="DONE"`) по `candidate_id` (переиспользован `get_candidate_id` из E5-02), затем
  скачивание `Answer.file` через S3. Оба блока результата — `{"available": bool, "bytes": ...}`,
  `S3 get_object` ошибка (файл удалён через 30 дней) ловится и не падает — `available: False`,
  export продолжается. 4 теста: оба файла доступны / видео истекло (resume не затронут) / нет
  `ResumeExtract` / неизвестный `candidate_profile_id`. Полный набор — 166 пройдено.
