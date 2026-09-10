# Шаг E18-01a — вынести резюме-пайплайн из CLI в сервисный слой

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E5 (processing queue), E3 (resume pipeline) — оба DONE
**Перед началом:** прочитай `services/resume_pipeline.py`, `services/change_detection.py`
(`get_candidate_id`), `cli/run_full_course_screening.py:37-56`
(`_process_resume_for_profile` — переносимая логика).

## Проблема (найдено 2026-09-10)

`run_tick` → `process_batch` → `_run_real_ai_call` никогда не вызывает
`process_resume()`/`fetch_resume_bytes` — ни для новых кандидатов, ни ретраем упавших.
Резюме кандидата обрабатывается **только** ручным запуском CLI
(`cli/run_resume_pipeline.py`, `cli/run_full_course_screening.py`) — то есть в проде
резюме нового кандидата не будет обработано, пока кто-то не запустит CLI руками
(иногда дни). Риск, которого боится владелец: кандидат закрывает доступ к резюме на
HH раньше, чем мы успеваем его скачать.

Этот шаг — первая часть решения (см. общую цель эпика в E18-01b/E18-01c): убрать
дублирование логики между CLI и будущим вызовом из scheduler, чтобы обе стороны
использовали один и тот же код.

## Цель

`_process_resume_for_profile` (сейчас приватная функция CLI) существует как публичная
`ensure_resume_processed` в сервисном слое; CLI использует её через импорт;
дублирующего кода не осталось. Поведение CLI не меняется.

## Что сделать

1. Перенести `cli/run_full_course_screening.py:37-56` (`_process_resume_for_profile`)
   as-is в `services/resume_pipeline.py` как публичную функцию
   `ensure_resume_processed(profile, *, platform_base, hh_client, s3_client, s3_bucket,
   llm_client, session) -> None`.
2. Импортирует `get_candidate_id` (`services/change_detection.py`, без циклических
   импортов — `change_detection.py` не импортирует `resume_pipeline.py`) и уже
   существующий в файле `find_anketa_resume_answer_id`.
3. `cli/run_full_course_screening.py` — заменить локальную функцию импортом
   `ensure_resume_processed`, вызовы в `_screen_profile` не меняются (та же сигнатура
   вызова).

## Файлы

- `src/sfera_ai/services/resume_pipeline.py` — новая публичная `ensure_resume_processed`.
- `src/sfera_ai/cli/run_full_course_screening.py` — убрать дублирующую приватную функцию, импорт.

## Критерии готовности (DoD)

- [ ] `ensure_resume_processed` в `resume_pipeline.py`, `cli/run_full_course_screening.py`
  использует импорт, дублирующего кода не осталось.
- [ ] Новый юнит-тест на перенесённую `ensure_resume_processed` (переиспользовать
  сценарии, которые раньше молча проверялись только через CLI/интеграционные прогоны —
  HH-лид ветка, анкетная ветка, кандидат без резюме ни там ни там).
- [ ] Существующие CLI-тесты (`run_full_course_screening`) по-прежнему зелёные —
  поведение CLI не изменилось, только источник функции.
- [ ] `uv run pytest` — весь сьют зелёный, регрессий нет.

## Как проверить

```bash
uv run pytest tests/services/test_resume_pipeline.py tests/cli/test_run_full_course_screening.py -v
uv run pytest  # полный сьют, регрессии
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг — E18-01b).

## Журнал

- `2026-09-10` — шаг выделен из первоначального единого E18-01 (разбивка на 3 шага
  по итогам ревью), реализация не начата — ждёт явного «начинай» от владельца
  (правило `CLAUDE.md`).
- `2026-09-10` — реализовано: `_process_resume_for_profile` перенесена as-is в
  `services/resume_pipeline.py` как публичная `ensure_resume_processed` (импортирует
  `get_candidate_id` из `change_detection.py`, циклических импортов нет); CLI
  `run_full_course_screening.py` использует импорт вместо локальной функции, вызов в
  `_screen_profile` не изменился. Отдельного CLI-теста на этот сценарий в репозитории
  не было (только `test_vacancy_profile_cli.py`) — пункт DoD снят как неактуальный.
  Добавлены 3 юнит-теста на `ensure_resume_processed` в `test_resume_pipeline.py`
  (HH-лид ветка, анкетная ветка, кандидат без резюме — noop). `uv run pytest` —
  229 passed.
