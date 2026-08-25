# Технический контекст фичи

> Что уже есть в коде, на что опираемся, какие ограничения. Прочитать до любого шага.

## Где живут видеовизитки

- **Модель ответа:** `sfera_backend/testchecks/models.py` → `Answer`
  - `question` (FK) — если `question.question_type == QuestionType.VIDEO_RECORDING` → это видеовизитка.
  - `file = FileField(upload_to='answer_file/')` — сам видеофайл.
  - `attempt` (FK → `TestAttempt`), `answered_at`.
  - Уникальность: один `Answer` на пару (attempt, question).
- **Тип вопроса:** `core/constants.py` → `QuestionType.VIDEO_RECORDING`.
- **Приём ответа:** `testchecks/views.py` (~строки 280–320) — `perform_create`, авто-завершение попытки
  «когда отвечены все ОБЯЗАТЕЛЬНЫЕ вопросы». ← сюда вешаем сигнал постановки в очередь (step-02).
- **Валидация видео:** `testchecks/serializers.py` — лимит `MAX_MB_VIDEO_ANSWER`.

## Хранилище файлов

- `core/s3.py`: `s3_enabled()` (== `settings.USE_S3_STORAGE`), клиент boto3 к **Timeweb S3**.
- В dev при `USE_S3_STORAGE=false` — локальный диск.
- ⚠️ Провайдер транскрибации НЕ должен предполагать локальный путь. Читать через
  `answer.file.open()` / storage-API — работает и с S3, и с диском. Для ffmpeg — сначала скачать во временный файл.

## Фоновая обработка (на что опираемся)

- **APScheduler**, вынесен в отдельный процесс: `core/scheduler.py`, команда
  `core/management/commands/run_scheduler.py`. В `docker-compose.staging.yml` — отдельный сервис
  `scheduler` (`command: python manage.py run_scheduler`). **Celery/Redis нет и не вводим.**
- **Готовый паттерн ffmpeg-обработки видео:** `lessons/services/video_processing.py` — как запускается
  ffmpeg/ffprobe через subprocess, обработка ошибок. Транскрибация повторяет этот паттерн.
- **Автоочистка:** `core/scheduler.py` → `clean_expired_videos()` удаляет `VIDEO_RECORDING`-ответы
  старше **30 дней**. `check_disk_pressure()` — удаляет старые видео при нехватке места (в S3-режиме пропускается).

## Раздел «Кандидаты» (куда выводим результат)

- **Frontend:** `SPHERA/src/domains/Candidate/`
  - `model/candidate-model.ts` — типы `CandidateAnswerItem` (уже есть `fileUrl`, `isVideoAnswer`),
    `CandidateDetails`, `CandidateLessonAnswers`. ← сюда добавляем поля транскрипта/summary.
  - `lib/candidate-answers-mapper.ts` — маппинг ответа API → модель.
- **Backend:** `testchecks/` (ответы), `courses/` (applications), сериализатор ответов кандидата.
- Доп. доки потока: `SPHERA/docs/CANDIDATE_APPLICATIONS_HR.md`, `CANDIDATE_COURSE_FLOW.md`.

## Архитектурные правила проекта (не нарушать)

- **BFF:** фронт ходит только в свой `/api` (Next), без прямого CORS к Django. Новые поля отдаём
  через существующий BFF-путь карточки кандидата.
- **FSD** на фронте, **RBAC**: транскрипт/summary видят только HR/Admin (не кандидат).
- Детали «что нельзя ломать» — `project-context/04_DECISIONS_AND_RISKS.md`.

## Новые зависимости (минимум)

- `faster-whisper` (Python-пакет, CTranslate2 под капотом — CPU int8, без GPU). + модель скачивается один раз.
- `ffmpeg` — **уже стоит** (используется в `lessons/`, есть в Dockerfile).
- LLM-клиент: HTTP к GigaChat/прокси (можно `requests`, уже в зависимостях) — без тяжёлых SDK.
