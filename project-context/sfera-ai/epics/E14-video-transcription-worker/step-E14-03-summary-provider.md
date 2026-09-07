# Шаг E14-03 — SummaryProvider (LLM-пересказ)

**Статус:** DONE (2026-09-07)
**Слой:** Backend · **Зависит от:** — (независим от E14-01/02 по коду, но логически нужен воркеру E14-04)
**Репозиторий:** `sfera_backend` — требует отдельного явного разрешения владельца перед
стартом (`CLAUDE.md`).
**Перед началом:** прочитай `project-context/PLATFORM_video-transcription-plan/step-04-summary-provider.md`
(интерфейс, промпт-шаблон, крайние случаи, DoD).

## Цель

Из транскрипта — краткий пересказ содержания (о чём говорит кандидат). Решено владельцем
2026-09-07: провайдер `gpt-4o-mini` через прокси, **без** классификации/вердикта.

## Где делать

`sfera_backend/testchecks/services/transcription/` — `ProxyLLMProvider` (`gpt-4o-mini`
через proxyapi/vsegpt) + модель/конфиг `SummaryPromptTemplate` (Django-admin, редактируется
без релиза).

## Файлы

- `sfera_backend/testchecks/services/transcription/summary.py` — новый (или соседний модуль)
- `sfera_backend/testchecks/models.py` — `SummaryPromptTemplate`
- env: `SUMMARY_PROVIDER=proxy`, `SUMMARY_MODEL=gpt-4o-mini`, `PROXY_API_KEY`

## Критерии готовности (DoD)

Полный список — в `step-04-summary-provider.md`. Кратко:
- [ ] Непустой транскрипт → осмысленный пересказ.
- [ ] Пустой транскрипт → сообщение о тишине без вызова LLM.
- [ ] Невалидный JSON-ответ не роняет воркер.

## Как отметить выполнение

1. Журнал в `step-04-summary-provider.md`.
2. Статус здесь → `DONE`, обнови `01_STATE.md` внешнего плана.
3. Обнови `04_STATE.md` этого репозитория.

## Журнал

- 2026-09-07: реализовано в `sfera_backend`, детали — журнал `step-04-summary-provider.md`
  внешнего плана. Верификация запуском не сделана (нет локального окружения в этой сессии),
  нужен ручной прогон тестов владельцем.
