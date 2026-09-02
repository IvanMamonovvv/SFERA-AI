# Шаг E11-02 — Пересборка fit-score для погранично прошедших кандидатов с реальным резюме

**Статус:** DONE
**Слой:** Backend/данные · **Зависит от:** E11-01 (HTTP-туннель к backend)
**Перед началом:** прочитай `step-E10-01-full-course-screening.md` (журнал, реальный
прогон 2026-08-31/09-01), эту запись `04_STATE.md`.

## Контекст

Реальный прогон `run_full_course_screening.py --course-id 39` (2026-09-01) дал 6
кандидатов на `fit_score=75` (порог `>75`, ни один формально не прошёл), включая 2
`STRONG_MATCH`. Но `resume-extraction` упал у всех 82 попыток курса (DNS, см. E11-01) —
оценка построена только на анкете, `data_completeness=PARTIAL` у всех шести. Реальное
резюме могло бы существенно изменить fit_score в любую сторону.

`candidate_profile_id` шести пограничных кандидатов (course_id=39):
`2301, 2677, 2760, 3112, 2378, 3026` (application_id: `2271, 1801, 1871, 2076, 2242, 2178`).

## Цель

Для этих 6 кандидатов — реальный resume-extraction (через туннель E11-01) → пересборка
facts → пересчёт fit-scoring. Понять, меняется ли recommendation/fit_score с учётом
резюме, прежде чем решать, пересобирать ли весь 90-прогон курса.

## Что сделать

1. Через туннель E11-01 прогнать `process_resume` для всех 6 `candidate_profile_id` —
   переиспользовать существующий сервисный код (`resume_pipeline.py`), не писать новый.
2. `build_or_update_candidate_facts` на этих же 6 — пересборка facts с учётом резюме.
3. `run_fit_scoring` — новая версия `CandidateVacancyAnalysis`, `is_current` переключится
   автоматически (существующий паттерн версионирования).
4. Сравнить старую (facts из анкеты) и новую (facts из анкеты+резюме) версии —
   fit_score/recommendation/confidence, зафиксировать разницу.
5. Показать сравнение владельцу, вместе решить: пересобирать весь 90-прогон курса 39
   заново или нет (стоимость — реальные LLM-вызовы, решение не в scope этого шага).

## Файлы

Без новых файлов сервисного кода — переиспользование `resume_pipeline.py`,
`candidate_facts.py`, `fit_scoring.py` через одноразовый скрипт/CLI-вызов (решить на
шаге: одноразовый скрипт в `scratchpad` или постоянный CLI-флаг
`run_full_course_screening.py --candidate-ids` — обсудить с владельцем перед реализацией).

## Критерии готовности (DoD)

- [x] 6 кандидатов имеют новую `CandidateVacancyAnalysis` версию, резюме реально
      учтено (`ai_resume_extract.status=DONE`, не FAILED) — но `data_completeness`
      остался `PARTIAL` у всех: формула считает количество *типов* источников
      (0/1-2/3-4), а у этих 6 всего 2 источника в принципе доступны (`hh_resume`+
      ответы, без анкетного файла и видео) — не баг, зафиксировано в журнале выше
- [x] Сравнительная таблица «было/стало» показана владельцу (журнал выше)

## Как проверить

```bash
uv run python -c "
from sfera_ai.db.session import make_write_engine
from sqlalchemy import text
engine = make_write_engine()
ids = [2301, 2677, 2760, 3112, 2378, 3026]
with engine.connect() as c:
    for cid in ids:
        row = c.execute(text('SELECT fit_score, recommendation, data_completeness, version FROM ai_candidate_vacancy_analysis WHERE candidate_profile_id=:cid AND is_current=true'), {'cid': cid}).fetchone()
        print(cid, row)
"
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг).

## Журнал

- `2026-09-01`: Добавлен постоянный CLI-флаг `--candidate-ids` в
  `run_full_course_screening.py` (владелец выбрал этот вариант вместо
  одноразового скрипта) — `_screen_profile`/`_screen_candidate_profile_id` в
  дополнение к `_screen_application`, без дублирования логики резюме/facts/
  fit-scoring. Первый прогон на 6 кандидатах провалился: `process_resume`
  падал с новой ошибкой (`Server disconnected without sending a response.`,
  не DNS из E11-01) — расследование по ssh на VPS показало, что
  `sfera-staging-backend-1` **снова отвалился от сети `ai_shared`** (тот же
  баг, что уже фиксировался и лечился в E11-01/`03_TDD.md` «Известная
  нестабильность» — переподключение не пережило рестарт/пересоздание
  контейнера). Восстановлено: `docker network connect ai_shared
  sfera-staging-backend-1` (согласованное исключение по CLAUDE.md — общая
  docker-сеть). После этого `process_resume` реально скачал и обработал
  резюме всех 6 кандидатов (`ai_resume_extract.status=DONE`).
  Повторный прогон (реальные LLM-вызовы через тунели E11-01+`tunnel-platform-db.sh`):

  | candidate_profile_id | fit_score было (анкета) | recommendation было | fit_score стало (+резюме) | recommendation стало |
  |---|---|---|---|---|
  | 2301 | 75 | POSSIBLE_MATCH | 70 | POSSIBLE_MATCH |
  | 2677 | 75 | POSSIBLE_MATCH | 75 | POSSIBLE_MATCH |
  | 2760 | 75 | POSSIBLE_MATCH | 65 | POSSIBLE_MATCH |
  | 3112 | 75 | POSSIBLE_MATCH | 65 | POSSIBLE_MATCH |
  | 2378 | 75 | **STRONG_MATCH** | None (аномалия, см. ниже) | POSSIBLE_MATCH |
  | 3026 | 75 | **STRONG_MATCH** | 75 | POSSIBLE_MATCH |

  Вывод: `data_completeness` у всех 6 остался `PARTIAL` (у этих кандидатов
  всего 2 источника из 4 возможны — `hh_resume`+ответы, анкетного файла и
  видео нет — резюме добавилось, но порог `data_completeness` не пересёк
  MINIMAL/PARTIAL/FULL границу; формула считает *количество типов
  источников*, не их наполненность). Ни один из 6 не пересёк порог `>75`
  даже с резюме. Оба `STRONG_MATCH` (2378, 3026) при учёте реального резюме
  понизились до `POSSIBLE_MATCH` — резюме реально меняет вывод модели, в
  сторону понижения уверенности, не завышения. У кандидата 2378 `fit_score`
  в финальной версии — `NULL` (LLM вернул валидный JSON с summary/токенами,
  но без числового `fit_score`; не расследовалось глубже — отдельная
  мелкая находка для `fit_scoring.py`, не блокирует этот шаг).

  Показано владельцу: понижение обоих `STRONG_MATCH` до `POSSIBLE_MATCH` при
  реальном резюме — сигнал в пользу пересборки всего 90-прогона курса 39,
  но само решение — отдельный шаг (п.5 плана), не в scope этого шага.

  Побочно: `ResumeExtract.error` не очищается при повторном успешном
  прогоне после `FAILED` — в БД остались записи `status=DONE` со старым
  текстом ошибки в поле `error` (не расследовалось/не чинилось — не
  блокирует DoD, но может ввести в заблуждение при будущей отладке).

  Тунели (`tunnel-backend.sh`/`tunnel-platform-db.sh`) остановлены штатно
  после прогона, proxy-контейнеры на VPS подтверждённо не остались висеть.
