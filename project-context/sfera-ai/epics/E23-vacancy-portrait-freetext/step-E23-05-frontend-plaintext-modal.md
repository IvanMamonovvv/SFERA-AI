# Шаг E23-05 — модалка SPHERA: обычный текст вместо JSON

**Статус:** DONE
**Слой:** Frontend (`SPHERA`, ДРУГОЙ репозиторий — разрешение владельца на эту конкретную
правку получено 2026-09-10, см. `04_STATE.md`) · **Зависит от:** E23-04
**Перед началом:** прочитай `SPHERA/src/domains/CandidateScreening/model.ts`,
`repositories/candidate-screening-repository.ts`,
`widgets/CandidatesWorkspace/CandidateScreeningModal.tsx` — текущая реализация делает
`JSON.parse`/валидацию JSON перед отправкой.

## Цель

HR-менеджер видит обычное текстовое поле «Портрет вакансии» (без слова JSON), пишет
свободный текст, опционально добавляет ссылку на источник — никакого JSON руками.

## Что сделать

1. `model.ts` — `VacancyProfileModel` получает `portraitText: string`, `sourceUrl: string |
   null` (вместо/вместе с `requirements`, если `requirements` ещё нужен для отображения —
   решить по месту, минимально — заменить на новые поля).
2. `candidate-screening-repository.ts`:
   - `mapVacancyProfile` — читает `portrait_text`/`source_url` из ответа `GET`;
   - `saveVacancyProfile(courseUuid, portraitText: string, sourceUrl: string | null)` —
     шлёт `{ portrait_text: portraitText, source_url: sourceUrl }` вместо `{ requirements }`.
3. `CandidateScreeningModal.tsx`:
   - убрать `JSON.parse`/`requirementsError`-валидацию целиком;
   - textarea предзаполняется `profile.portraitText` (обычный текст, не
     `JSON.stringify(requirements)`);
   - лейбл `htmlFor="vacancy-requirements"` → «Портрет вакансии» (без «(JSON)»), плейсхолдер —
     пример обычного текста («Менеджер по продажам, опыт B2B от 2 лет, холодные звонки...»);
   - новое опциональное текстовое поле «Ссылка на вакансию» рядом с textarea, значение —
     `sourceUrl`, передаётся в `saveVacancyProfile`;
   - обработка ошибки: 422 от бэка (`InvalidVacancyRequirementsResponse` через прокси) →
     `showToast` с текстом ошибки вместо старого клиентского «Невалидный JSON».

## Файлы

- `SPHERA/src/domains/CandidateScreening/model.ts`
- `SPHERA/src/domains/CandidateScreening/repositories/candidate-screening-repository.ts`
- `SPHERA/src/widgets/CandidatesWorkspace/CandidateScreeningModal.tsx`
- `SPHERA/src/widgets/CandidatesWorkspace/CandidateScreeningModal.module.scss` — стили под
  новое поле ссылки, при необходимости

## Критерии готовности (DoD)

- [ ] textarea не требует JSON, любой обычный текст сохраняется
- [ ] поле «Ссылка на вакансию» опционально, пустое — не блокирует сохранение
- [ ] повторное открытие модалки показывает ранее введённый текст-портрет (не JSON)
- [ ] ошибка от бэка (невалидный LLM-ответ) видна пользователю понятным тостом
- [ ] `npm run typecheck`/`lint` (или эквивалент проекта) — без ошибок

## Как проверить

Ручная проверка в браузере (dev-сервер SPHERA): открыть модалку «Обработка кандидатов»,
ввести текст портрета без JSON, сохранить, убедиться что скрининг кандидатов запускается.

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (этого репо,
   SFERA-AI — трекинг эпика централизован здесь, по паттерну E14/E15).

## Журнал

- `2026-09-10` — `model.ts`: `VacancyProfileModel.requirements` заменён на `portraitText`/`sourceUrl`.
  `candidate-screening-repository.ts`: `mapVacancyProfile` читает `portrait_text`/`source_url`,
  `saveVacancyProfile(courseUuid, portraitText, sourceUrl)` шлёт `{ portrait_text, source_url }`
  (контракт бэкенда `VacancyProfileCreate` и прокси `sfera_ai_proxy_views.py` уже принимали эти
  поля — E23-04 реализован раньше). `CandidateScreeningModal.tsx`: убран `JSON.parse`/
  `requirementsError`, лейбл «Портрет вакансии» без «(JSON)», текстовый плейсхолдер, новое поле
  «Ссылка на вакансию» (`sourceUrlInput` в `.module.scss`). Ошибка от бэка (422) и так шла через
  `parseApiErrorPayload`/`error.message` в существующий `catch` — отдельный код не понадобился.
  `tsc --noEmit`/`eslint` по изменённым файлам — чисто.
