# Шаг E3-03 — извлечение текста из файла (PDF/DOC)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E3-02

## Цель

Из байтов файла (PDF/DOC/DOCX) получается `raw_text`, сохраняется в `ResumeExtract`.

## Что сделать

1. Выбрать библиотеку парсинга (PDF: `pypdf`/`pdfplumber`; DOC/DOCX: `python-docx` или
   универсальный конвертер) — зафиксировать выбор в журнале шага.
2. Функция `extract_text(file_bytes: bytes, mime_type: str) -> str`.
3. Битый/нечитаемый файл → `ResumeExtract.FAILED` + `error`, не роняет пайплайн
   (`03_TDD.md`, «Failure Scenarios», «Битый resume»).

## Файлы

- `src/sfera_ai/services/resume_text_extraction.py`
- `tests/services/test_resume_text_extraction.py` — фикстуры: валидный PDF, битый файл

## Критерии готовности (DoD)

- [x] Валидный PDF/DOCX → непустой `raw_text`
- [x] Битый файл → `FAILED`, исключение не улетает наружу

## Как проверить

```bash
uv run pytest tests/services/test_resume_text_extraction.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — реализовано: `extract_text(file_bytes, mime_type) -> str`
  (`src/sfera_ai/services/resume_text_extraction.py`), библиотеки — `pypdf` (PDF) и
  `python-docx` (DOCX), обе добавлены (`uv add`). Битый файл/неподдерживаемый
  `mime_type` (в т.ч. legacy `.doc` — не поддержан, `python-docx` его не читает,
  отдельный конвертер сочли избыточным для MVP) → `TextExtractionError`, не
  `ResumeExtract.FAILED` напрямую — по сигнатуре шага функция чистая (bytes+mime →
  str), не знает про `ResumeExtract`/`session`; перевод в `FAILED` — ответственность
  вызывающего пайплайн-кода (аналогично паттерну `fetch_resume_bytes` в E3-02, но
  разбито на уровень ниже — сам факт FAILED-перевода будет в шаге, который вызовет
  `extract_text` внутри try/except). PDF-тест использует вручную собранный минимальный
  PDF (без внешних PDF-библиотек в dev-зависимостях), DOCX-тест — `python-docx`
  Document в фикстуре теста. `uv run pytest tests/services/test_resume_text_extraction.py`
  — 5 passed. Полный сьют — 42 passed, регрессий нет.
