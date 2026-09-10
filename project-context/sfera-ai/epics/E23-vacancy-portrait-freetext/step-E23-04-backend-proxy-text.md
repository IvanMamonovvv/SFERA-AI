# Шаг E23-04 — прокси `sfera_backend` пропускает текст вместо JSON

**Статус:** DONE
**Слой:** Backend (`sfera_backend`, ДРУГОЙ репозиторий — разрешение владельца на эту
конкретную правку получено 2026-09-10, см. `04_STATE.md`) · **Зависит от:** E23-03
**Перед началом:** прочитай `sfera_backend/sfera_backend/courses/sfera_ai_proxy_views.py`
(`VacancyProfileProxyView.post`) и `integrations/sfera_ai/client.py::create_vacancy_profile` —
оба сейчас хардкодят `requirements: dict`.

## Цель

Прокси между SPHERA и SFERA-AI пропускает `portrait_text`/`source_url` вместо требования
готового JSON `requirements` — иначе новый формат из E23-03 никогда не доедет до SFERA-AI.

## Что сделать

1. `VacancyProfileProxyView.post` — валидация меняется: `portrait_text: str` (непустая
   строка, обязателен), `source_url: str | None` (опционален). Убрать проверку
   `isinstance(requirements, dict)`.
2. `integrations/sfera_ai/client.py::create_vacancy_profile` — сигнатура
   `(course_uuid, *, portrait_text: str, source_url: str | None = None,
   created_by_id: int | None = None)`, тело запроса `{'portrait_text', 'source_url', 'notes',
   'created_by_id'}` вместо `{'requirements', ...}`.
3. `GET`/`fetch_vacancy_profile` — не трогать, ответ SFERA-AI проксируется как есть, новые
   поля `portrait_text`/`source_url` из E23-03 пройдут насквозь без изменений на этом слое.
4. **Блокер, найден архитектурным ревью 2026-09-10:** `_sfera_ai_error_response`
   (`sfera_ai_proxy_views.py:27-36`) сейчас режет ЛЮБУЮ ошибку SFERA-AI до жёсткого текста
   `{'detail': 'SFERA-AI вернул ошибку.'}` — реальная причина 422 (`InvalidVacancyRequirementsResponse`,
   "LLM вернул невалидный JSON" и т.п.) до фронта не доходит. Без этого DoD шага E23-05
   ("ошибка видна пользователю понятным тостом") недостижим. Завести спецкейс: при
   `status_code == 422` доставать `detail` из тела ответа SFERA-AI (проверить, что `SferaAiError`/
   `_request` вообще сохраняет распарсенный JSON-body, а не только `resp.text[:500]` — если нет,
   доработать) и возвращать его как есть, `{'detail': <реальный текст>}`, статус 422. Общий
   generic-текст оставить только для остальных статусов (5xx/сетевые сбои).

## Файлы (обновлено)

## Файлы

- `sfera_backend/sfera_backend/courses/sfera_ai_proxy_views.py` — валидация запроса +
  `_sfera_ai_error_response`/422 passthrough
- `sfera_backend/sfera_backend/integrations/sfera_ai/client.py` — форма тела запроса,
  проверить/доработать `SferaAiError` на предмет хранения распарсенного JSON-тела ошибки
- `sfera_backend/sfera_backend/courses/tests/test_sfera_ai_proxy_views.py` — обновить кейсы +
  новый кейс: 422 от SFERA-AI → реальный `detail` доходит до ответа проксирующего view как есть
- `sfera_backend/sfera_backend/integrations/sfera_ai/tests/test_client.py` — обновить кейсы

## Критерии готовности (DoD)

- [x] POST с `portrait_text`(+опционально `source_url`) проходит проверку, доходит до SFERA-AI
      в новом формате
- [x] POST без `portrait_text` (пусто/отсутствует) — понятная 400-ошибка
- [x] 422 от SFERA-AI (невалидный LLM-ответ) → реальный текст причины доходит до клиента
      проксирующего endpoint'а как есть, не generic "SFERA-AI вернул ошибку."
- [x] старые тесты, ссылавшиеся на `requirements`, переписаны под новый контракт, не удалены
      молча
- [x] полный тест-сьют `sfera_backend` по затронутым модулям — зелёный

## Как проверить

```bash
# в sfera_backend
pytest sfera_backend/courses/tests/test_sfera_ai_proxy_views.py -v
pytest sfera_backend/integrations/sfera_ai/tests/test_client.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (этого репо,
   SFERA-AI — трекинг эпика централизован здесь, по паттерну E14/E15).

## Журнал

- `2026-09-10` — реализовано в `sfera_backend` (репо `FullSphera`): `VacancyProfileProxyView.post`
  валидирует `portrait_text` (непустая строка, обязателен) вместо `requirements: dict`,
  `source_url` опционален; `create_vacancy_profile` в `client.py` шлёт
  `{portrait_text, source_url, notes, created_by_id}`. `SferaAiError` получил `response_body`
  (распарсенный JSON тела ошибки, `_request` пытается `resp.json()`, `None` при не-JSON).
  `_sfera_ai_error_response` — спецкейс на `status_code == 422`: достаёт `detail` из
  `response_body`, отдаёт как есть, при отсутствии тела — fallback на старый generic-текст.
  Тесты обновлены под новый контракт (`test_sfera_ai_proxy_views.py`,
  `test_client.py`) + новые кейсы (пустой `portrait_text` → 400, 422 passthrough с телом
  и без). Полный сьют `manage.py test courses integrations.sfera_ai` — 222 теста, зелёный.
  Отступлений от плана нет.
