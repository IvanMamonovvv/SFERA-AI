# Шаг E17-03 — Склейка резюме в один PDF с карточкой

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E17-02 (резюме реально прикладывается),
E9-03 (`archive.py` — текущий формат ZIP, согласован с владельцем 2026-08-31)
**Перед началом:** прочитай `src/sfera_ai/services/export/archive.py`
(`build_candidates_export_archive`, `_sniff_resume_extension`),
`src/sfera_ai/services/export/files.py` (`collect_export_files` — что возвращает
`resume["bytes"]`/`source_type`), `src/sfera_ai/services/resume_text_extraction.py`
(уже использует `pypdf`/`python-docx` — переиспользовать паттерн, не плодить второй).

## Контекст

Сейчас (`archive.py`) `card.pdf` и `resume.<ext>` — отдельные файлы в ZIP-подпапке
кандидата, формат явно согласован с владельцем 2026-08-31 (`step-E9-03`). Владелец
2026-09-10 решил: резюме должно идти следующими страницами того же PDF, что и
карточка — не отдельным файлом. `pypdf`/`python-docx` уже в зависимостях
(`pyproject.toml`) — новых пакетов не требуется.

Ограничение: резюме бывает не только PDF (`_sniff_resume_extension` различает
`pdf`/`docx`/`bin` по магическим байтам уже сейчас) — HH резюме, как правило, PDF
(`hh_client.get_resume_pdf`), но `ANKETA_FILE` (загруженный кандидатом на платформу
файл, `testchecks_answer.file`) может быть любым форматом, включая `.doc`/`.docx`/
изображение. Для не-PDF резюме нужна конвертация в PDF перед merge — либо страница-
заглушка «резюме приложено отдельным файлом, формат <ext> не поддерживает
предпросмотр» как fallback, если конвертация недоступна без системных зависимостей
(тот же компромисс, что был у E9-01/E9-04 — reportlab выбран, чтобы не тащить
cairo/pango в Docker; DOCX→PDF без LibreOffice/системных пакетов не делается
надёжно — **обсудить с владельцем перед реализацией**, не проектировать конвертацию
заранее).

## Цель

Экспорт кандидата — один PDF-файл: страница(ы) `render_ai_card_pdf` + следующими
страницами резюме (если PDF) либо явная заглушка (если формат резюме не PDF и
конвертация не сделана).

## Что сделать

1. **Согласовать с владельцем** сценарий для не-PDF резюме до кода: (a) заглушка-
   страница с пояснением + оставить прежний ZIP как fallback вариант для таких
   кандидатов, (b) подключить конвертацию (какой инструмент — обсудить, LibreOffice
   headless утяжелит Docker-образ), (c) не поддерживать смерджить — только PDF-резюме
   мерджится, остальное — как сейчас (отдельный файл в ZIP рядом).
2. `merge_card_with_resume(card_pdf: bytes, resume_bytes: bytes | None, resume_ext:
   str | None) -> bytes` — новый helper (файл ниже), `pypdf.PdfWriter`/`PdfReader`,
   по образцу использования `pypdf` в `resume_text_extraction.py`.
3. `archive.py`: заменить `archive.writestr(f"{folder}/resume.{ext}", ...)` на вызов
   merge перед записью `card.pdf`, по решению п.1 для не-PDF случая.
4. `manifest.txt`-поведение сохранить для случая, когда резюме недоступно вообще
   (`resume["available"] is False`) — здесь ничего не меняется, merge просто не
   происходит.
5. Видео (`video.mp4`) остаётся отдельным файлом в ZIP — владелец просил склейку
   только для резюме, видео нельзя показать как страницы PDF.

## Файлы

- `src/sfera_ai/services/export/pdf_merge.py` (новый) или функция в `ai_card.py` —
  решить по объёму при реализации
- `src/sfera_ai/services/export/archive.py` — интеграция merge вместо отдельного файла
- `tests/services/test_export_archive.py`, новый `tests/services/test_pdf_merge.py`

## Критерии готовности (DoD)

- [x] Решение по не-PDF резюме зафиксировано в журнале до кода (п.1)
- [x] PDF-резюме — итоговый файл в ZIP одна `card.pdf` со страницами карточки +
      резюме, не два отдельных файла
- [x] Резюме недоступно (`available=False`) — поведение `manifest.txt` не изменилось
- [x] `uv run pytest` — полный сьют зелёный

## Как проверить

```bash
uv run pytest tests/services/test_export_archive.py tests/services/test_pdf_merge.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг,
   эпик E17 → DONE, если это последний шаг).

## Журнал

- 2026-09-10 — **Решение владельца (п.1):** не-PDF резюме (`docx`/`bin`) — страница-
  заглушка в `card.pdf` («резюме приложено отдельным файлом, формат .<ext> не
  поддерживает предпросмотр») + сам файл резюме дополнительно кладётся в ZIP как
  раньше (`resume.<ext>`, fallback вариант). PDF-резюме — только merge страниц,
  отдельный файл не пишется. Конвертация docx→pdf не подключается (владелец не
  выбрал вариант с LibreOffice).
- 2026-09-10 — Реализовано: `pdf_merge.py` (`merge_card_with_resume`,
  `_stub_page_pdf` через reportlab, тот же `DejaVuSans`/`_STYLES` что в
  `ai_card.py`), `archive.py` — merge вместо отдельного `resume.pdf` для PDF-
  резюме; `card.pdf` недоступен (`pdf is None`) — резюме пишется отдельным файлом
  как раньше, merge не применяется. Тесты: `tests/services/test_pdf_merge.py`
  (unit на `merge_card_with_resume` — без резюме/PDF-резюме/не-PDF заглушка) +
  3 новых теста в `test_export_archive.py` (merge PDF, заглушка+ZIP-fallback,
  резюме без карточки). `uv run pytest` — 220 passed.
