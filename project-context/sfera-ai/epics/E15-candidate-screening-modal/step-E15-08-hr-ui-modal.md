# Шаг E15-08 — Кнопка и модалка «Обработка кандидатов» (фронтенд)

**Статус:** DONE
**Слой:** Frontend (`SPHERA`) · **Зависит от:** E15-06
**Репозиторий:** `SPHERA` — требует отдельного явного разрешения владельца перед
стартом (`CLAUDE.md`).
**Перед началом:** прочитай `docs/superpowers/specs/2026-09-08-candidate-screening-modal-design.md`
целиком (UI-раздел «Поток», «Frontend»).

## Цель

HR видит кнопку «Обработка кандидатов» рядом с «Выгрузить архив», может править
портрет вакансии, видеть ранжированный список прошедших кандидатов и выгружать
карточки — без прямого похода в SFERA-AI.

## Что сделать

1. Кнопка «Обработка кандидатов» в разделе кандидатов курса, рядом с «Выгрузить архив».
2. Модалка: textarea портрета (предзаполнена текущим `VacancyProfile.requirements`),
   список кандидатов (`fit_score` отображается как X/10, округление `floor`, см.
   E15-03), бейдж «уже передан», кнопки «выгрузить карточку»/«выгрузить список».
3. «Сохранить» → запрос к новому проксирующему endpoint'у FullSphera (E15-06), не к
   SFERA-AI напрямую. Модалка закрывается сразу после ответа, без поллинга прогресса
   (согласовано явно владельцем — раздел «Поток», п.4 дизайн-документа).

## Файлы

- `src/domains/Candidate/` (или соответствующий раздел курса) — найти при реализации.

## Критерии готовности (DoD)

- [ ] Кнопка видна только там, где уже видна «Выгрузить архив» (тот же уровень доступа).
- [ ] Textarea предзаполняется текущим портретом, если он есть.
- [ ] Список сортирован по убыванию, бейдж «передан» корректен.
- [ ] «Сохранить» закрывает модалку сразу, без ожидания прогресса обработки.
- [ ] Экспорт (одиночный/массовый) вызывает проксирующий endpoint, не SFERA-AI.

## Как проверить

Ручная проверка в браузере на демо-курсе (`run` скилл/dev-сервер SPHERA) — золотой
путь + пустой список (курс без прошедших порог кандидатов).

## Как отметить выполнение

1. Журнал в этом файле. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` этого репозитория.

## Журнал

- `2026-09-09` — реализовано по явному разрешению владельца. По ходу реализации
  найдены и закрыты (с отдельным согласованием владельца) три расхождения дизайна с
  уже сданными шагами E15-03/06/07:
  1. **`requirements` — JSON, не текст.** `POST vacancy-profile/` (и SFERA-AI, и
     проксирующий endpoint) жёстко требует `requirements: dict`, конвертации
     текст→JSON на этом пути нет (`build_vacancy_requirements` — только в отдельном
     CLI E10). Решение владельца: textarea показывает
     `JSON.stringify(requirements, null, 2)`, HR правит как текст, «Сохранить» делает
     `JSON.parse` и шлёт dict; невалидный JSON — инлайн-ошибка, модалка не закрывается,
     запрос не уходит.
  2. **Не было `GET vacancy-profile/` прокси** — E15-06/07 сделали только `POST`,
     без него нечем предзаполнить textarea (явный DoD). Добавлен `GET` в тот же
     `VacancyProfileProxyView` (переименован из `VacancyProfileProxyCreateView`) +
     `fetch_vacancy_profile` в `integrations/sfera_ai/client.py` (404 от SFERA-AI →
     `None`, не ошибка — портрета ещё не было).
  3. **В `GET candidates/screening/` не было ключа для сопоставления с фронтендом.**
     `candidate_profile_id` — внутренний id SFERA-AI, платформе (и `candidateStore`
     SPHERA) неизвестный; имени/email кандидата в ответе нет вообще (сознательно,
     «поля как в `candidates/`», E8-02). Добавлено поле `application_id` (nullable —
     `null` у HH-лидов без `Application`) в `list_screening_candidates`
     (`services/api_read.py`, SFERA-AI) — фронтенд ищет по нему в уже загруженном
     `candidateStore.candidates` за именем/email; без совпадения — `Отклик #<id>`.
  Также найден и исправлен смежный баг общей инфраструктуры SPHERA: BFF-прокси
  `src/app/api/proxy/[[...path]]/route.ts` конвертировал тело ответа через `.text()` —
  портило бы бинарный `application/zip` при экспорте. Исправлено на `arrayBuffer()` +
  проброс `Content-Disposition` (безопасно и для существующих JSON-ответов).

  Новый код (`SPHERA`): домен `domains/CandidateScreening/` (`model.ts`,
  `repositories/candidate-screening-repository.ts` — GET/POST через
  `restProviderInstance`, экспорт — отдельный `fetch` на `/api/proxy/...` с
  `credentials: "include"`, т.к. `RestProvider` всегда парсит JSON и не умеет blob);
  `shared/lib/download-blob-file.ts` (по образцу `download-text-file.ts`); виджет
  `CandidateScreeningModal.tsx` (+ `.module.scss`) — по образцу `CandidateMergeModal.tsx`
  (тот же `Modal`, та же state-machine `loading/ready/error`). Кнопка «Обработка
  кандидатов» в `CandidatesWorkspace.tsx` — рядом с «Выгрузить архив», без
  дополнительного `appRole`-гейта (тот же уровень доступа, что и у экспорта —
  экспорт тоже не гейтится ролью). «Выгрузить список» — экспортирует всех
  показанных в модалке кандидатов одним zip (выбора чекбоксами дизайн не описывал).
  После любого экспорта список кандидатов перезапрашивается — обновляет бейджи
  «передан» с бэкенда, а не оптимистично.

  Правки в `sfera_backend`: `VacancyProfileProxyView` (GET+POST),
  `integrations/sfera_ai/client.py::fetch_vacancy_profile`, новые тесты в
  `test_sfera_ai_proxy_views.py`/`integrations/sfera_ai/tests/test_client.py`.
  Правки в `SFERA-AI`: `api_read.py::_application_id_by_candidate_profile` +
  поле `application_id` в `list_screening_candidates`, тест в
  `tests/api/test_candidates_list.py` дополнен двумя assert.

  Проверено: `npx tsc --noEmit` и `eslint --fix` по правленым файлам SPHERA — чисто
  (один pre-existing `react-hooks/exhaustive-deps` warning в `CandidatesWorkspace.tsx`,
  подтверждён `git stash` — не от этой правки). `manage.py test` весь `sfera_backend` —
  684 passed, 3 skipped, регрессий нет. `uv run pytest` весь `SFERA-AI` — 205 passed.
  Ручная проверка в браузере (golden path + пустой список) **не выполнена** — нет
  запущенного dev-сервера SPHERA/staging окружения в этой сессии; DoD «как проверить»
  остаётся открытым пунктом для владельца перед мержем. Ничего не закоммичено ни в
  одном из трёх репозиториев — ждёт решения владельца по коммиту/PR.
