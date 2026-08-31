# Шаг E9-04 — стилизация AI-карточки (визуал как в ai-screening-hub)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E9-01 (текущий рендер на reportlab, эта функция
переписывается, сигнатура не меняется — E9-03 не блокируется этим шагом)
**Перед началом:** прочитай `step-E9-01-ai-card-pdf.md` (журнал — почему выбран
reportlab, а не WeasyPrint: без системных зависимостей cairo/pango в Docker-образе).
Референс визуала — `ai-screening-hub/backend/app/templates/vacancy_card.html` и
`ai-screening-hub/backend/app/services/pdf_card.py` (другой репозиторий,
`/Users/proskurkin-va/Documents/projects/ParserResumeHH/` — код не импортируется,
только визуальный референс).

## Цель

`render_ai_card_pdf` рендерит карточку с тем же визуальным стилем, что карточка
кандидата в ai-screening-hub (чёрная плашка, цветные блоки, таблица баллов с
цветовой индикацией) — но остаётся на `reportlab` (без WeasyPrint/HTML), чтобы не
тащить cairo/pango в Docker. Один кандидат — одна страница, оценка и информация о
кандидате не разбиваются на разные страницы.

## Что сделать

1. **Извлечение ФИО** (сделать первым — без этого не собрать заголовок карточки).
   `_SYSTEM_PROMPT` в `services/resume_extraction.py:12-17` — добавить `full_name`
   (строка, ФИО кандидата) в список полей, которые просит вернуть LLM. Старые
   `ResumeExtract.structured_data` без `full_name` — карточка не падает, фолбэк
   `"Кандидат #<candidate_profile_id>"`.
2. **Перевод confidence на русский.** Сверить в БД реальные значения `confidence`,
   которые пишет E6 fit-scoring, затем словарь-маппинг на русские подписи (низкая/
   средняя/высокая). Неизвестное значение — fallback `"—"`, не падать.
3. **Маппинг полей** `CandidateVacancyAnalysis`/`CandidateProfile` → карточка:
   `full_name` (п.1), `recommendation`, `strengths`, `gaps` (блок "что уточнить"),
   `criteria_scores` (dict → таблица критерий/балл), `fit_score`, `confidence` (п.2,
   переведено), `facts` из `CandidateProfile` (блок "данные платформы").
4. **Пересборка рендера** в `ai_card.py` — вместо `SimpleDocTemplate`/списка
   `Paragraph`, собрать документ из `Table`-блоков с `TableStyle` (цветной фон,
   `LINEBEFORE` для акцентной полосы слева, per-cell цвет текста) под референс
   `vacancy_card.html`:
   - чёрная плашка сверху (однострочная `Table`, чёрный фон/белый текст)
   - ФИО + подзаголовок (синий `#2a5db0`)
   - без фото кандидата (нет доступа к файлу резюме в SFERA-AI)
   - блок рекомендации — фон `#fff4e5`, акцент слева `#e8871e`
   - два столбца "сильные стороны" (`#1a7a3c`) / "что уточнить" (`#a6390d`)
   - серый блок "данные платформы" (`#eef2f7`) — факты профиля
   - таблица баллов — цвет числа по порогу (≥8 зелёный `#1a7a3c`, ≥5 оранжевый
     `#b35c00`, иначе красный `#a6390d`)
   - итоговая строка — `fit_score` + переведённая уверенность
   - футер — серый текст по центру
5. **Тесты.** `tests/services/test_ai_card_export.py` — обновить под новую сборку
   (проверка, что PDF генерируется и не пустой, не сверка визуала — как в E9-01).
   Добавить сценарий: `structured_data` без `full_name` → карточка не падает,
   fallback-текст на месте имени.
6. **Зависимости.** Не менять — `reportlab` уже есть, `pyproject.toml`/`Dockerfile`
   не трогать.

## Файлы

- `src/sfera_ai/services/export/ai_card.py` — пересборка рендера
- `src/sfera_ai/services/resume_extraction.py` — `full_name` в `_SYSTEM_PROMPT`
- `tests/services/test_ai_card_export.py` — тесты под новый рендер

## Критерии готовности (DoD)

- [x] Карточка визуально повторяет структуру `vacancy_card.html` (чёрная плашка,
      цветные блоки, таблица баллов) средствами reportlab, без новых зависимостей
- [x] Один кандидат — одна страница, без разрыва между инфо и оценкой
- [x] `full_name` подставляется из `structured_data`, fallback работает на старых
      резюме без этого поля
- [x] `confidence` выводится по-русски, fallback на неизвестное значение
- [x] PDF генерируется на кандидате с полными данными и на кандидате с частичными
      (не падает на отсутствующих полях — facts/strengths/gaps пустые, fit_score=None)
- [x] `uv run pytest tests/services/test_ai_card_export.py -v` проходит

## Как проверить

```bash
uv run pytest tests/services/test_ai_card_export.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-31 — `ai_card.py` пересобран на `Table`-блоках (reportlab, без WeasyPrint):
  чёрная плашка, синий подзаголовок, блок рекомендации с акцентной полосой
  (`LINEBEFORE`), два столбца сильные стороны/что уточнить, серый блок платформы,
  таблица баллов с цветом по порогу (≥8/≥5/иначе), итоговая строка, футер. Вся
  карточка обёрнута в `KeepTogether` — не разбивается между страницами.
  `full_name` — из последнего `ResumeExtract.status="DONE".structured_data["full_name"]`
  по `candidate_profile_id` (сортировка по `id desc`); `_SYSTEM_PROMPT` в
  `resume_extraction.py` дополнен полем `full_name`. `candidate_display_name`
  получил опциональный второй параметр `full_name` (обратная совместимость с
  `archive.py`, который продолжает звать без него — там fallback умышленно не менялся,
  вне периметра этого шага). `CONFIDENCE_RU` — сверено с `fit_scoring.py:16`
  (`_CONFIDENCE_CHOICES = {"LOW", "MEDIUM", "HIGH"}`), маппинг не менялся.
  8 тестов в `test_ai_card_export.py` (было 4): + display_name с/без full_name,
  + рендер с `ResumeExtract` (есть full_name / нет full_name → fallback). Полный
  прогон `uv run pytest tests/ -q` — 176 passed.
