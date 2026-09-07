# Шаг E14-02 — TranscriptionProvider (whisper)

**Статус:** TODO
**Слой:** Backend · **Зависит от:** — (независим от E14-01, можно параллельно)
**Репозиторий:** `sfera_backend` — требует отдельного явного разрешения владельца перед
стартом (`CLAUDE.md`).
**Перед началом:** прочитай `project-context/PLATFORM_video-transcription-plan/step-03-transcription-provider.md`
(интерфейс, ffmpeg-извлечение аудио, крайние случаи, DoD).

## Цель

Абстракция «видео → текст» с реализацией self-hosted `faster-whisper`, переключаемая по env.

## Где делать

`sfera_backend/testchecks/services/transcription/base.py` (новый модуль) —
`TranscriptionProvider` Protocol + `LocalFasterWhisperProvider` (модель-синглтон на
процесс, `language=ru`, `WHISPER_MODEL_SIZE=small` из спайка step-00). ffmpeg-паттерн — как
в `sfera_backend/lessons/services/video_processing.py`.

## Файлы

- `sfera_backend/testchecks/services/transcription/base.py` — новый
- env: `TRANSCRIBE_PROVIDER=local` (рубильник)

## Критерии готовности (DoD)

Полный список — в `step-03-transcription-provider.md`. Кратко:
- [ ] `local` провайдер транскрибирует тестовое русское видео в текст.
- [ ] Пустое/тихое видео → `is_empty=True`, без исключений.
- [ ] Временные файлы удаляются после обработки.

## Как отметить выполнение

1. Журнал в `step-03-transcription-provider.md`.
2. Статус здесь → `DONE`, обнови `01_STATE.md` внешнего плана.
3. Обнови `04_STATE.md` этого репозитория.

## Журнал

- (пусто)
