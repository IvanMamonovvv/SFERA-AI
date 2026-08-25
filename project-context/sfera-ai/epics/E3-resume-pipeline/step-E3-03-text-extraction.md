# Шаг E3-03 — извлечение текста из файла (PDF/DOC)

**Статус:** TODO
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

- [ ] Валидный PDF/DOCX → непустой `raw_text`
- [ ] Битый файл → `FAILED`, исключение не улетает наружу

## Как проверить

```bash
uv run pytest tests/services/test_resume_text_extraction.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано, какая библиотека выбрана и почему>.
