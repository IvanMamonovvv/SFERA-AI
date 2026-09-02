# Шаг E13-02 — Видимый флаг «нет резюме» для менеджера

**Статус:** TODO
**Слой:** Backend (services/CLI/API) · **Зависит от:** E13-01 (тот же контекст
приоритета источников), E9-04 (`ai_card.py` текущая вёрстка), E8-02/E8-03
(`api_read.py`), E10-01 (`run_full_course_screening.py`)
**Перед началом:** прочитай `src/sfera_ai/services/candidate_facts.py`
(`_completeness`, импорт `ResumeExtract`), `src/sfera_ai/models/resume_extract.py`
(`status` — значения `PENDING`/`DONE`/`FAILED`), `src/sfera_ai/cli/run_full_course_screening.py`
(`_FIELDNAMES`, `_screen_profile`/`_screen_application`/`_screen_candidate_profile_id`),
`src/sfera_ai/services/export/ai_card.py` (`_platform_block`, `render_ai_card_pdf`),
`src/sfera_ai/services/api_read.py` (`get_candidate_detail`, `list_candidates`),
[[project_source_priority_resume_answers_video]].

## Контекст

Сейчас отсутствие или ошибка резюме нигде явно не сигнализируется — `ResumeExtract`
со `status != "DONE"` просто не участвует в сборке фактов (`candidate_facts.py`),
менеджер не видит причину низкой уверенности оценки. Владелец подтвердил: это НЕ
должно блокировать кандидата (E13-01), но должно быть видно.

## Цель

В трёх местах вывода (CSV CLI-прогона, PDF-карточка, API) виден явный статус
резюме кандидата: есть / битое / отсутствует. Оценка при этом не блокируется —
только становится понятно, почему confidence/fit_score ниже.

## Что сделать

1. Новый helper в `src/sfera_ai/services/candidate_facts.py`, рядом с
   `_completeness` — `resume_status(resume_extracts: list[ResumeExtract]) ->
   Literal["MISSING", "FAILED", "OK"]`: пустой список → `MISSING`, есть хотя бы
   один `status == "DONE"` → `OK`, иначе (есть записи, но ни одной `DONE`) →
   `FAILED`. Принимает уже загруженный список (как в
   `build_or_update_candidate_facts:134-139`), не делает свой SQL-запрос —
   переиспользуется вызывающим кодом без дублирования запроса.
2. CLI (`run_full_course_screening.py`): добавить `resume_status` в `_FIELDNAMES`
   (строка ~23) и во все 4 места, где формируется dict-строка кандидата
   (`_screen_profile:66-74` и её error-ветка `76-84`, `_screen_application:94-102`,
   `_screen_candidate_profile_id:115-123`) — иначе `csv.DictWriter` упадёt на
   несовпадении fieldnames. В error-ветках, где `ResumeExtract` не подгружался —
   `None`/`"UNKNOWN"`.
3. PDF-карточка (`ai_card.py`): отдельный акцентный блок сразу после
   `_platform_block(facts)` в `render_ai_card_pdf` (после текущей строки ~241,
   по образцу `_recommendation_block:111-125`) — виден только когда
   `resume_status != "OK"`, текст «Резюме отсутствует» / «Резюме не удалось
   обработать» соответственно.
4. API: `get_candidate_detail` (`api_read.py:81`, `profile`/`facts` уже загружены
   на строках 101-102) — добавить `"resume_status"` на верхний уровень
   возвращаемого dict (рядом с `candidate_profile_id`/`current`/`facts`/`history`,
   строки 118-140). `list_candidates` (строка 230, элементы `items.append({...})`
   строки 271-280) — сейчас в цикле не загружается `CandidateProfile`/`ResumeExtract`,
   нужен батч-подзапрос по всем `candidate_profile_id` страницы (аналогично
   `_demo_progress_by_candidate_profile`, строка 182), не N+1 запросов на
   кандидата.
5. `get_summary` (агрегат по курсу) — вне scope этого шага (отдельная задача
   подсчёта "сколько кандидатов без резюме" на уровне курса, не по кандидату).

## Файлы

- `src/sfera_ai/services/candidate_facts.py` — новый helper `resume_status`
- `src/sfera_ai/cli/run_full_course_screening.py` — новая колонка CSV
- `src/sfera_ai/services/export/ai_card.py` — новый блок в PDF
- `src/sfera_ai/services/api_read.py` — новое поле в `get_candidate_detail` и
  `list_candidates`

## Критерии готовности (DoD)

- [ ] `resume_status` различает 3 состояния (MISSING/FAILED/OK), переиспользуется
      во всех 4 точках вставки без дублирования SQL-запроса на `ResumeExtract`
- [ ] CSV-прогон CLI не падает на `DictWriter` (все 4 dict-литерала синхронизированы
      с `_FIELDNAMES`)
- [ ] PDF-карточка показывает блок только когда резюме не `OK` — визуально
      проверено на кандидате без резюме и на кандидате с битым резюме
- [ ] `get_candidate_detail`/`list_candidates` отдают `resume_status` без N+1
      запросов на страницу кандидатов
- [ ] Кандидат без резюме НЕ получает hard-block/ошибку — оценка считается как
      обычно (E13-01), флаг только информативный
- [ ] `uv run pytest` — полный сьют зелёный, регрессий нет

## Как проверить

```bash
uv run pytest -q
# + ручной прогон CLI на 1-2 кандидатах без резюме, проверить CSV-колонку
# + сгенерировать PDF-карточку кандидата без резюме, глазами проверить блок
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг).

## Журнал

- (пусто)
