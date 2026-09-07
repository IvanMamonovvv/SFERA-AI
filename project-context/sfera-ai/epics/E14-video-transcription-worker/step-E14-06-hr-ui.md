# Шаг E14-06 — UI в карточке кандидата (HR/Admin)

**Статус:** TODO
**Слой:** Frontend · **Зависит от:** E14-05
**Репозиторий:** `SPHERA` (фронтенд, ещё один отдельный репозиторий) — требует отдельного
явного разрешения владельца перед стартом (`CLAUDE.md`).
**Перед началом:** прочитай `project-context/PLATFORM_video-transcription-plan/step-07-hr-ui.md`
(UX, крайние случаи, DoD).

## Цель

HR видит рядом с видеовизиткой: статус обработки, summary, раскрываемый транскрипт.

## Где делать

`SPHERA/src/domains/Candidate/model/candidate-model.ts` — расширить `CandidateAnswerItem`
полем `transcription` (без `verdict` — упрощено владельцем 2026-09-07). Маппер —
`lib/candidate-answers-mapper.ts`. Компонент отображения видеоответа — блок «Разбор
видеовизитки» (бейдж статуса, summary, спойлер транскрипта).

## Файлы

- `SPHERA/src/domains/Candidate/model/candidate-model.ts`
- `SPHERA/src/domains/Candidate/lib/candidate-answers-mapper.ts`
- компонент видеоответа в `domains/Candidate/` (найти при реализации)

## Критерии готовности (DoD)

Полный список — в `step-07-hr-ui.md`. Кратко:
- [ ] У обработанной визитки видно summary, транскрипт раскрывается.
- [ ] Пустое видео → понятная формулировка, не пустой блок.
- [ ] Кандидат этих данных не видит.

## Как отметить выполнение

1. Журнал в `step-07-hr-ui.md`.
2. Статус здесь → `DONE`, обнови `01_STATE.md` внешнего плана.
3. Обнови `04_STATE.md` этого репозитория.

## Журнал

- (пусто)
