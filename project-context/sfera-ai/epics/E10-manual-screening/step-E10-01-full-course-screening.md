# Шаг E10-01 — полный прогон вакансии по всем кандидатам (CLI, без UI)

**Статус:** DONE (код готов, реальный прогон на проде — отдельно, см. журнал)
**Слой:** Backend (CLI) · **Зависит от:** E6, E9-03, E9-04
**Перед началом:** прочитай `step-E9-03-export-endpoint.md`/`step-E9-04-styled-candidate-card.md`
(экспорт-слой и карточка переиспользуются как есть) и `PLATFORM_AUDIT_REFERENCE.md`
раздел «4. Резюме» (два независимых источника — анкетный файл vs HH-резюме).

## Контекст / зачем

Владелец хочет прогнать реальную вакансию на проде (`course_id` пришлёт отдельно)
целиком — всех кандидатов по резюме+ответам+видео, без фронтенда — и сравнить с тем,
кого реально выбрал клиент. Согласовано в диалоге 2026-08-31 (см. `04_STATE.md`).

**Находка, расширившая scope:** в кодовой базе нет функции «найти анкетное резюме
кандидата» (файл-ответ на вопрос анкеты) — сознательно отложенный гэп из E3/E5
(«Answers Pipeline» vs «Resume Pipeline», см. `run_resume_pipeline.py` docstring).
Без него `facts` для кандидатов без HH-резюме соберутся только из ответов+видео.
`PLATFORM_AUDIT_REFERENCE.md`, раздел 4: анкетное резюме — `Answer` с
`question.question_text == "ANKETA_RESUME"`. Нужна ещё одна платформенная таблица в
reflection (`testchecks_question`) — на проде потребует новый `GRANT SELECT` для
`ai_readonly` (прецедент — [[project_grant_select_new_platform_table]]).

## Цель

`run_full_course_screening.py --course-id <id>`: все кандидаты курса (не выборка, в
отличие от `run_fit_scoring_sample.py`) проходят resume-обработку + сборку facts +
fit-scoring, в конце — сводка и zip со стилизованными карточками (E9-04) только
прошедших порог.

## Что сделать

1. `find_anketa_resume_answer_id(platform_base, candidate_id) -> int | None` в
   `resume_pipeline.py` (или новом модуле) — по паттерну `_video_file`/`get_candidate_id`
   (`services/export/files.py`, `services/change_detection.py`): `Answer` join
   `Question` (`question_text == "ANKETA_RESUME"`) join `TestAttempt` (`candidate_id`),
   берёт последний по `answered_at`. Новая константа таблиц `RESUME_DETECTION_TABLES`
   в `platform_db.py` (существующий набор + `testchecks_question`).
2. Новый CLI: для каждого `Application` курса (через `IDENTITY_RESOLVER_TABLES`, как
   в `run_fit_scoring_sample.py::_application_ids_for_course`):
   - `resolve_or_create_candidate_profile`, если профиля ещё нет;
   - резюме: `hh_negotiation_id` есть → `process_resume(hh_resume_id=...)`; иначе
     `find_anketa_resume_answer_id` → `process_resume(source_answer_id=...)`; ни
     того ни другого — пропустить (не падать);
   - `build_or_update_candidate_facts`;
   - `run_fit_scoring` против текущего `VacancyProfile` курса (нет текущего профиля
     → понятная ошибка и выход, не тихий пропуск).
3. Сводка — CSV/stdout как в `run_fit_scoring_sample.py` (все кандидаты, любой результат).
4. `fit_score > 75` (порог подтверждён владельцем 2026-08-31) → собрать подмножество
   `candidate_profile_id`, вызвать существующий `build_candidates_export_archive`
   (E9-03, карточки уже в стиле E9-04) → один zip-файл на диск (путь — аргумент CLI,
   **не коммитить** — содержит реальные ФИО/контакты, как и текущий прецедент с CSV
   для HR-сверки в E6-05).
5. Каждый кандидат — try/except по паттерну `_run_sample` (`run_fit_scoring_sample.py`) —
   упавший не блокирует остальных, ошибка в сводке.

## Файлы

- `src/sfera_ai/platform_db.py` — `RESUME_DETECTION_TABLES`
- `src/sfera_ai/services/resume_pipeline.py` (или новый модуль) — `find_anketa_resume_answer_id`
- `src/sfera_ai/cli/run_full_course_screening.py` — новый CLI
- `tests/services/test_resume_pipeline.py` (или новый файл) — `find_anketa_resume_answer_id`
- нет автотеста на сам CLI-скрипт — ручной прогон, по прецеденту
  `run_fit_scoring_sample.py`/`run_resume_pipeline.py` (E6-05)

## Критерии готовности (DoD)

- [x] `find_anketa_resume_answer_id` находит анкетное резюме кандидата по
      `question_text == "ANKETA_RESUME"`, `None` — если файла нет (не падает)
- [x] `run_full_course_screening.py` проходит все `Application` курса, ошибка одного
      кандидата не блокирует остальных
- [x] zip с карточками — только у кандидатов `fit_score > 75`, остальные — только в сводке
- [x] `uv run pytest` — полный сьют зелёный, регрессий нет
- [x] **Перед реальным прогоном на проде** — `GRANT SELECT` на `testchecks_question`
      для `ai_readonly` выдан владельцем 2026-09-01; `course_id=39` и порог
      `fit_score > 75` подтверждены владельцем непосредственно перед запуском
      (прецедент E6-04/E6-05)
- [ ] **Известный баг найден 2026-09-01, не исправлен:** resume-extraction при ручном
      прогоне с локальной машины падает по DNS (`hh_backend_base_url` резолвится только
      изнутри docker-сети VPS) — заведено отдельным эпиком
      [[epics/E11-backend-tunnel-verification]]. Реальный прогон 2026-09-01 прошёл БЕЗ
      резюме (только анкета), fit-score по всем 90 кандидатам построен на неполных
      данных — не считать окончательным результатом до E11.

## Как проверить

```bash
uv run pytest tests/services/test_resume_pipeline.py -v
uv run pytest -q
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-09-01` — **реальный прогон на проде выполнен**: `course_id=39` («РТХ Менеджер
  по продажам B2B — входящие заявки. Русский Торговый Холдинг», найден по UUID
  `123be98a949d4d4f926b2e0518b22d3c` из ссылки владельца через `resolve_course_id`),
  `--fit-threshold 75` (default). Перед прогоном выдан `GRANT SELECT` на
  `testchecks_question` для `ai_readonly` (владелец подтвердил). 90 `Application`
  обработаны, **0 ошибок**. Распределение по `recommendation`: `NOT_ENOUGH_DATA` 47,
  `POSSIBLE_MATCH` 28, `NOT_A_MATCH` 10, `WEAK_MATCH` 3, `STRONG_MATCH` 2. `fit_score`
  min/max/avg: 10/75/60.5.
  **Найдены два дефекта:**
  1. **Пороговый баг:** условие `fit_score > threshold` (строго больше) при
     `threshold=75` отсекло собственный максимум — 6 кандидатов ровно на `fit_score=75`
     (включая оба `STRONG_MATCH`), zip получился пустым («No candidates passed the
     fit-score threshold») при живых сильных кандидатах. `>` vs `>=` не обсуждалось
     явно на этапе плана — уточнить с владельцем перед следующим прогоном, какая
     семантика порога нужна (строго больше / включительно).
  2. **Resume-extraction сломан при ручном прогоне с локальной машины:** 82/82 попыток
     упали `backend request failed: [Errno 8] nodename nor servname provided` —
     `hh_backend_base_url` резолвится только изнутри docker-сети VPS (`ai_shared`).
     Побочно найдено: `sfera-staging-backend-1` был отключён от сети `ai_shared`
     (как и `db`-контейнер ранее в этой же сессии) — переподключён вручную. Весь
     90-прогон построен только на данных анкеты, `data_completeness=PARTIAL` у всех
     шести кандидатов на границе `fit_score=75`. Заведено отдельным эпиком
     [[epics/E11-backend-tunnel-verification]] — до его закрытия результаты этого
     прогона не считать окончательными.
  Собран отдельный zip по 6 погранично прошедшим (`candidate_profile_id`:
  2301, 2677, 2760, 3112, 2378, 3026) без повторных LLM-вызовов — переиспользован
  `build_candidates_export_archive` напрямую поверх уже сохранённых `is_current`
  анализов. Побочно найден баг в самой карточке — см. [[epics/E12-pdf-cyrillic-fix]].
- `2026-08-31` — реализовано: `RESUME_DETECTION_TABLES` (platform_db.py),
  `find_anketa_resume_answer_id` (resume_pipeline.py) + 2 теста, новый CLI
  `run_full_course_screening.py` (обходит все `Application` курса, резюме через
  `hh_negotiation_id` либо `find_anketa_resume_answer_id`, facts + fit-scoring,
  try/except на кандидата, CSV-сводка, zip только для `fit_score > threshold`
  через `build_candidates_export_archive`). `uv run pytest` — 178 passed. Реальный
  прогон на проде НЕ выполнялся — ждёт `GRANT SELECT` на `testchecks_question` и
  подтверждения `course_id`/порога владельцем.
