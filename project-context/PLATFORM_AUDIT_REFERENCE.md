# Технический аудит SFERA — база для проектирования AI-модуля анализа кандидатов

Дата аудита: 2026-08-21. Метод: чтение реального кода (Django backend `sfera_backend/`, Next.js frontend `SPHERA/`) через codegraph-индекс + прямые прочтения файлов. Документация project-context/ использовалась как контекст, но везде, где она расходится с кодом или не покрывает вопрос, источник истины — код; расхождения отмечены явно. Ничего в проекте не менялось.

---

## 1. Общая архитектура

**Frontend**: Next.js (App Router), TypeScript, MobX, FSD (Feature-Sliced Design). Папка `SPHERA/src/`. BFF-паттерн: фронт ходит только в свой `/api/*` (Next API routes), без прямого CORS к Django. Например `SPHERA/src/app/api/hh-resume` проксирует backend-эндпоинт резюме HH.

**Backend**: Django 5.x + Django REST Framework, Python. Папка `sfera_backend/sfera_backend/`. JWT-аутентификация (`simple_jwt`). Apps: `users`, `courses`, `lessons`, `testchecks`, `companies`, `integrations` (headhunter, wazzup), `core`, `api` (роутинг), `sent_emails` (не app — просто dev-директория для filebased email backend).

**ORM / БД**: Django ORM, PostgreSQL 17 в проде (`docker-compose.staging.yml`, сервис `db: postgres:17`); локально допускается SQLite.

**Файловое хранилище**: Timeweb Cloud S3-совместимое хранилище (`s3.twcstorage.ru`), включается флагом `USE_S3_STORAGE` (`core/s3.py`, `settings.py:280-319`, `django-storages` + `boto3`). Без флага — локальный `FileSystemStorage` (dev). MinIO не используется.

**Очередь задач**: Celery/Redis/RQ — **НЕ НАЙДЕНО**. Единственный механизм фоновых задач — **APScheduler 3.10.4** (`core/scheduler.py`), работающий как отдельный долгоживущий процесс.

**Cron/scheduler**: тот же APScheduler, ~12 зарегистрированных job'ов (транскодинг видео уроков, чистка мусора, весь цикл HH-синхронизации, сборка ZIP-архивов кандидатов и их очистка). Запускается командой `python manage.py run_scheduler`, в проде — отдельный Docker-сервис `scheduler` (тот же образ, что backend, другая команда), сознательно вынесен из gunicorn-воркеров, чтобы не плодить по инстансу планировщика на воркер и изолировать CPU-нагрузку ffmpeg от веб-запросов.

**Фоновые workers**: нет отдельного worker-пула — APScheduler крутит job'ы внутри одного процесса `scheduler` через `ThreadPoolExecutor` (20 воркеров) с `max_instances=1` на большинство задач (не дублируются, если предыдущий запуск не завершился).

**Внешние сервисы**: HeadHunter API (OAuth2 + webhook-приёмник, `integrations/headhunter/`), Wazzup (`integrations/wazzup/`), Timeweb S3, SMTP (в проде) / filebased email (dev).

**Прод-инфраструктура**: VPS Timeweb `5.42.120.39`, Ubuntu 24.04. Новый backend-стек — `/var/www/sfera-backend/`, порт **8081**, `docker-compose.staging.yml` (сервисы `db`, `backend`, `scheduler`, `gateway`=nginx), деплой вручную по SSH через `scripts/deploy-backend.sh` (git pull → `docker compose up -d --build` → migrate → collectstatic). CI/CD для backend не найден (есть только у фронтенда). Фронт задеплоен отдельно на `https://sphera-link.online`. **Важно**: в `project-context/09_BACKEND_DEPLOY.md` описан ещё старый прод (чужой, "бекендеров", порт 8080, `sferatest.ddns.net`, Docker Hub образы) — на момент аудита неясно, произошёл ли уже cutover; **ТРЕБУЕТ УТОЧНЕНИЯ у владельца**, какой из двух прод-адресов актуален сейчас.

**Части системы, отвечающие за кандидатов**: `users` (модель пользователя-кандидата), `courses` (Application, Progress, CandidateArchiveJob, CandidateMergeLog + вьюхи списка/деталей кандидата), `testchecks` (Test/Question/Answer/TestAttempt — ответы демонстрации, включая видео), `integrations/headhunter` (лиды HH до регистрации, резюме HH).

---

## 2. Сущность кандидата

Отдельной модели `Candidate` **нет**. Кандидат — это `CustomUser` с `role=CANDIDATE`.

**`CustomUser`** — `sfera_backend/sfera_backend/users/models.py:16`, таблица `users_customuser`, наследует `AbstractUser`.

| Поле | Тип | Комментарий |
|---|---|---|
| `id` | AutoField (PK) | **стабильный уникальный ID кандидата** |
| `name` | CharField | ФИО |
| `email` | EmailField, unique | `USERNAME_FIELD` |
| `phone` | CharField, nullable | |
| `role` | CharField (choices) | `UserRole.CANDIDATE` и др. роли (`core/constants.py:113-123`) |
| `company` | FK → `companies.Company`, SET_NULL | |
| `registration_uuid` | UUIDField, unique | |
| `registration_status` | CharField (choices) | |
| `consent_to_data_processing` / `_at` | Boolean / DateTime | 152-ФЗ |
| `consent_to_mailing` / `_at` | Boolean / DateTime | |
| `accepted_terms` / `_at` | Boolean / DateTime | |
| `first_name`, `last_name` | — | явно обнулены, не используются |

⚠️ У `CustomUser` **нет** `created_at`/`updated_at` (не наследует `CreatedModifiedBaseModel`, в отличие от почти всех остальных моделей проекта). Дата регистрации приблизительно восстановима через `date_joined` (поле `AbstractUser`) — **ТРЕБУЕТ УТОЧНЕНИЯ**, используется ли оно фактически.

**Рекомендация для AI-модуля: использовать `CustomUser.id` (PK) как стабильный `candidate_id` во всей системе** — на него ссылаются `Application.candidate`, `TestAttempt.candidate`, `Progress.candidate`, `CandidateLesson.candidate`.

Также в `users/models.py:115`: `DataDeletionLog` — журнал hard-delete по 152-ФЗ (email_masked, email_hash, deleted_at, performed_by, reason) — не относится к кандидату напрямую, но важно для privacy-контекста AI-модуля (после удаления пользователя данные пропадают).

**status/progress/score живут не на User**, а распределены по связанным моделям — см. разделы 3, 6, 7.

---

## 3. Связь кандидата с вакансией

Промежуточная таблица — **`Application`** (`sfera_backend/sfera_backend/courses/models.py:87`, таблица `courses_application`).

```
candidate (FK CustomUser, CASCADE, related_name=candidate_applications)
course    (FK Course,     CASCADE, related_name=course_applications)
status    (CharField, choices ApplicationStatus: NEW/VIEWED/ACCEPTED/REJECTED)
comment   (TextField, nullable)
source    (CharField, choices ApplicationSource, default ORGANIC)
merged_into (self-FK, SET_NULL — для дедупликации кандидатов)
created_at / updated_at (CreatedModifiedBaseModel)
```
`UniqueConstraint(course, candidate)` — **один Application на пару (курс, кандидат)**. Один кандидат (`CustomUser`) **может** иметь несколько `Application` на разные курсы/вакансии — отдельная запись создаётся на каждый курс.

Полей `progress`, `hh_vacancy_title`, `hh_resume_id`, `hh_negotiation_pk` **в самой `Application` нет** — это либо вычисляемые serializer-поля (progress), либо приходят из связанной `HHNegotiationRecord` (HH-поля).

**До того как кандидат реально стартует прохождение**, отклик с HH существует как **`HHNegotiationRecord`** (`integrations/headhunter/models.py:199`) — "лид" без `User`/`Application`, идентифицируется `enrollment_token` (UUID, персональная ссылка из сообщения), несёт снэпшоты `candidate_name/city/email_snapshot/phone_snapshot`. После реального старта прохождения создаётся `Application`, и `HHNegotiationRecord.application` (OneToOne) связывает их. **Важный нюанс для инкрементального анализа**: пока лид не стартовал демонстрацию, `candidate_id` (User.id) вообще не существует — есть только `HHNegotiationRecord.pk` + email/phone-снэпшот. Если ТЗ требует анализировать "всех кандидатов независимо от % прохождения", нужно явно решить — входят ли сюда HH-лиды без Application (только резюме/анкетные данные с hh.ru, без демонстрации).

`Course` — модель курса/демонстрации (`courses/models.py`), содержит `purpose` (учебный/демо, отдельная фича) — вакансия в системе фактически = курс с привязанной через `VacancyCourseMapping` (`integrations/headhunter/models.py:135`) HH-вакансией (`hh_vacancy_id`, `hh_vacancy_title`).

---

## 4. Резюме

Отдельной модели `Resume` **нет**. Два независимых источника:

**(а) Анкетное резюме** — файл, загруженный кандидатом как ответ на вопрос анкеты (`ANKETA_RESUME`). Физически это строка **`Answer`** (`testchecks/models.py:130`, таблица `testchecks_answer`) с `question.question_text == ANKETA_RESUME`, поле `file = FileField(upload_to='answer_file/')`. Формат — что кандидат загрузит (обычно PDF/DOC), явных ограничений формата в модели не видно (**ТРЕБУЕТ УТОЧНЕНИЯ** в сериализаторе приёма файла — `courses/serializers.py:308-328`, `resume = FileField(...)`, `validate_resume`). Storage — тот же S3/local, что и остальные `Answer.file`.
- Дата появления/изменения: `Answer.answered_at` (auto_now_add) + `created_at`/`modified_at` (`CreatedModifiedBaseModel`). Поскольку `Answer` имеет `UniqueConstraint(attempt, question)`, **финализированный ответ с резюме перезаписать нельзя** — значит `answered_at` фиксирует единственный момент появления.
- Может отсутствовать: да, если кандидат не дошёл до этого вопроса анкеты или вопрос не обязателен (`is_required=False`).

**(б) HH-резюме** — не файл, а строковый идентификатор `hh_resume_id` в **`HHNegotiationRecord`** (`integrations/headhunter/models.py:199`). PDF **не хранится** в системе — подтягивается динамически по запросу через `GET /api/v1/companies/{slug}/integrations/hh/negotiations/{pk}/resume.pdf/` (`HHResumePdfView`, `integrations/headhunter/views.py:157-195`), который проксирует HH API (`services.get_resume_pdf`). Значит: **распарсенного текста/JSON резюме нигде нет** — ни для анкетного файла, ни для HH-резюме. Для AI-модуля это первая точка, где потребуется добавить парсинг (extract text из PDF/DOC).
- Связь с candidate_id: `HHNegotiationRecord.application` (OneToOne на `Application`, которая ссылается на candidate) — после старта; до старта связи с `candidate_id` нет вообще (см. раздел 3).

Резюме может отсутствовать полностью (ни анкетного файла, ни HH-резюме — если, например, кандидат зашёл по прямой ссылке без HH).

---

## 5. Видеовизитка / видео-ответы

Storage: тот же Timeweb S3, отдельный namespace ключей — `answer_video/{attempt_id}/{question_id}/{uuid4().hex}{ext}` (`testchecks/services/media_paths.py`), не пересекается с видео уроков (`course_media/`).

Модель ответа с видео — та же **`Answer`** (`testchecks/models.py:130`), поле `file` для видео фактически хранит **S3-ключ**, а не файл, загруженный через Django. Видеовизитка отличается от обычного видео-ответа теста флагом **`Question.is_video_intro = True`** (`testchecks/models.py:84-92`) — используется именно для сборки архива резюме+видео.

Промежуточная модель **`AnswerVideoUpload`** (`testchecks/models.py:170`) — факт "видео залито в S3, ждёт привязки к Answer", до финализации: `attempt` FK, `question` FK, `object_key`, `status` (`UPLOADED`/`CONFIRMED`, только 2 статуса). `UniqueConstraint(attempt, question)`.

- **Перезапись до финализации**: да, `update_or_create` в `AnswerVideoUploadConfirmView` (`testchecks/views.py:477-537`) — старый S3-объект детектируется и best-effort удаляется (`client.delete_object`, ошибка только логируется).
- **После финализации (Answer создан) — перезаписать НЕЛЬЗЯ**: `Answer.UniqueConstraint(attempt, question)` + `IntegrityError` → 400 "Ответ на этот вопрос уже был отправлен." Старое видео не сохраняется отдельно — оно единственное.
- Обработка видео (ffmpeg/транскодинг): **есть, но только для видео УРОКОВ от админа** (`lessons/services/video_processing.py`, модель `LessonMedia`) — 720p H.264/AAC, faststart. **Видео-ответы кандидата (включая видеовизитку) НЕ обрабатываются вообще** — ни транскодинга, ни сжатия; явно задокументировано решение "без транскода" в `project-context/video-answer-upload-reliability/`.
- Транскрибация/STT: **НЕ РЕАЛИЗОВАНО**. Есть только план в `project-context/candidate-video-transcription/` (все 11 шагов TODO), согласованный стек — self-hosted `faster-whisper` + LLM-summary, очередь в БД, env-рубильник на cloud. Это прямое предзнание для проектируемого AI-модуля — вероятно, транскрибация видеовизиток будет frontend-частью того же будущего пайплайна.
- Ограничения: `MAX_MB_VIDEO_ANSWER = 150` МБ (`core/constants.py:228`), расширения `.mp4`/`.webm`, presigned URL живёт 15 минут. Ограничения по длительности для видео-ответов **не найдено** (есть только для видео уроков).
- Связь с candidate_id: `Answer.attempt` → `TestAttempt.candidate` (FK на `CustomUser`) — та же цепочка, что у ответов.
- `created_at`/`modified_at`/`answered_at` есть — можно надёжно определить момент появления нового видео (см. выше про неперезаписываемость финализированного `Answer`).

---

## 6. Ответы кандидатов

Реляционная схема, не JSON-блоб. Иерархия: **`Test` (=урок-тест) → `TestAttempt` (попытка) → `Answer` (один ответ на один вопрос)**.

**`Test`** (`testchecks/models.py:19`) — `lesson` FK.
**`TestAttempt`** (`testchecks/models.py:36`, таблица `testchecks_testattempt`) — `test` FK, `candidate` FK (CustomUser, CASCADE), `passed` (nullable Boolean), `score` (Integer), `max_score` (Integer), `started_at` (auto_now_add), `completed_at` (nullable DateTime).
**`Question`** (`testchecks/models.py:63`) — `test` FK, `question_type` (choices), `question_text` (TextField), `is_required`, `is_video_intro`.
**`OptionAnswer`** (`testchecks/models.py:111`) — варианты для SINGLE/MULTIPLE CHOICE, `text`, `is_correct`.
**`Answer`** (`testchecks/models.py:130`, таблица `testchecks_answer`) — `question` FK, `attempt` FK, `text` (JSONField, для текстовых/выбор ответов), `file` (FileField, для файлов/видео), `answered_at` (auto_now_add). `UniqueConstraint(attempt, question)` — **один ответ = одна запись, без переписывания после создания**.

- Текст вопроса хранится (`Question.question_text`); текст/значение ответа — в `Answer.text` (JSON) или `Answer.file`.
- Типы вопросов есть (`QuestionType` choices, включая текст, выбор, файл, видеозапись).
- Оценки: на уровне `TestAttempt` (score/max_score/passed), не на уровне отдельного `Answer`.
- Timestamps: `Answer.answered_at`, плюс `created_at`/`modified_at` от `CreatedModifiedBaseModel` на всех уровнях.
- **Определить "появился новый ответ после последнего AI-анализа"** — да, надёжно: сравнить `Answer.answered_at`/`created_at` с датой последнего анализа. Поскольку ответы неперезаписываемы после финализации, "новый ответ" = запись, которой не было при прошлом анализе; изменённых старых ответов быть не может (только новые).
- **Все ответы одного кандидата одним запросом**: да — `GET /api/v1/courses/{course_uuid}/candidates/{candidate_id}/answers/` (`CandidateCourseAnswersListView`, `testchecks/views.py:543-616`), отдаёт дерево `Lesson → tests → attempts → answers` за один вызов (см. раздел 9, п.3).

---

## 7. Процент прохождения демонстрации

**Не хранится как поле** — вычисляется. Модель **`Progress`** (`courses/models.py:149`) хранит "сырьё": `candidate` FK, `course` FK, `current_lesson` FK, `completed_lessons` (Int), `total_lessons` (Int), `completed_at` (nullable). `UniqueConstraint(course, candidate)`.

Расчёт процента — `SerializerMethodField.get_progress` в `CourseCandidatesBaseSerializer` (`courses/serializers.py:74-120`):
```python
def get_progress(self, obj):
    progress_score = getattr(obj, 'progress_score', None)  # если аннотировано в queryset
    if progress_score is not None:
        return int(progress_score)
    progress_obj = self._get_progress_obj(obj)               # Progress.objects.filter(candidate=, course=).first()
    if progress_obj and progress_obj.total_lessons > 0:
        return (progress_obj.completed_lessons / progress_obj.total_lessons) * 100
    return 0
```
Эта же формула продублирована в сервисе сборки ZIP-архива (`courses/candidates_archive_service.py`) как SQL-аннотация к queryset — **два места считают процент одинаковой логикой, не общая функция** (риск рассинхронизации при будущих изменениях — не трогать оба места одновременно без сверки).

- Завершением урока считается `CandidateLesson.is_completed=True` (`lessons/models.py:125`, `UniqueConstraint(candidate, lesson)`).
- Статусы: `Application.status` (NEW/VIEWED/ACCEPTED/REJECTED) — это статус **отклика** (workflow HR), не связан напрямую с % прохождения демонстрации. Это два независимых измерения кандидата.
- Видеовизитка на % не влияет напрямую — это просто ответ на один из вопросов урока; урок считается пройденным по `CandidateLesson.is_completed`, для чего видео-вопрос как и любой обязательный (`is_required=True`) должен быть отвечен.

---

## 8. Экспорт ZIP (архив резюме+видео+answers.csv)

**Это НЕ Celery/management-command, а APScheduler-job**, живущий в контейнере `scheduler`.

**Frontend → создание job'а**:
- `SPHERA/src/domains/CandidateArchive/store/candidate-archive-jobs-store.ts:73` `createJob(courseUuid, range)` → репозиторий → поллинг раз в 5с.
- `POST /api/v1/courses/{course_uuid}/candidates/resume-video-archive/` (body `{min_score, max_score}`).
- `GET .../resume-video-archive/{id}/` — статус.
- `POST .../resume-video-archive/{id}/cancel/`.
- Готовый файл скачивается прямой ссылкой `job.fileUrl` (без отдельного API-запроса на скачивание).

**Backend — создание job'а**: `CandidateArchiveJobCreateView` (`courses/views.py:562-624`) — если активный job с тем же диапазоном уже есть, возвращает его; если кандидатов в диапазоне нет — 204 без создания; иначе создаёт `CandidateArchiveJob(status=PENDING)`. **Синхронной сборки при запросе нет** — только запись в БД.

**Обработка**: `core/scheduler.py` регистрирует `process_candidate_archive_jobs` (interval ~15с, `max_instances=1`) → `courses/candidate_archive_job_processing.process_one_job()` — обрабатывает **ровно один** `PENDING`-job за тик (`select_for_update(skip_locked=True)`), т.е. очередь из нескольких job'ов идёт строго последовательно.

**Сборка `_build_zip(job)`** (`candidate_archive_job_processing.py:223`):
1. `collect_candidate_archive_entries(course, min_score, max_score)` (`courses/candidates_archive_service.py:149`) — аннотирует `progress_score` (та же формула, что раздел 7), фильтрует `Application` по диапазону, тремя батч-запросами достаёт: анкетное резюме (`Answer` где `question_text==ANKETA_RESUME`), видео-ответ (`Answer` где `is_video_intro=True`), HH-резюме (`application.hh_negotiation.hh_resume_id`).
2. `_collect_file_bytes` — параллельно (ThreadPoolExecutor, HH-пул 8 / copy-пул 12): анкетные файлы читаются через Django storage API (`field_file.open('rb')` — работает и с S3, и с локальным диском); HH-резюме — через `integrations.headhunter.services.get_resume_pdf` (тот же код, что публичный endpoint резюме).
3. Запись во временный zip-файл: `resumes/{Имя_Фамилия}{ext}`, `videos/{Имя_Фамилия}{ext}` (коллизии имён — суффикс `_2`, `_3`), с проверкой отмены на каждой итерации.
4. `answers.csv` строится отдельной функцией `build_archive_candidates_answers` (`courses/completed_candidate_answers.py`) — колонки: Имя, Email, Прогресс(%), Резюме(файл да/нет), Видеовизитка(файл да/нет), Дата отклика, Статус, ФИО/Телефон/Соцсеть(HH) + по колонке на вопрос анкеты. Кодировка `utf-8-sig`.
5. Заливка zip в S3: ключ `candidate_archives/{course_uuid}/{job.pk}.zip` (`archive_paths.py`), `job.status=READY`, `expires_at = now + 3 дня` (по умолчанию).
6. Очистка — отдельный cron-job `cleanup_expired_candidate_archives` (04:00 ежедневно): удаляет просроченные READY-архивы, переводит зависшие >2ч PROCESSING в FAILED.

**Использованные ID**: `Application.id`/`candidate.id`/`course.uuid`; имена файлов в архиве — по `User.name`, не по ID (коллизии решаются суффиксом).

**Вывод для AI-модуля**: функции `collect_candidate_archive_entries` (сбор источников по диапазону прогресса) и `build_archive_candidates_answers` (сбор ответов в табличном виде) — **готовые переиспользуемые строительные блоки** для сбора Candidate Profile без ZIP. AI-модулю ZIP не нужен вообще — эти же Django-queryset'ы/сервисы дают прямой программный доступ к резюме, видео и ответам без архивации.

Отдельно существует не связанный с архивом CSV-экспорт без файлов (`candidates_csv_answers_export` — три endpoint'а completed/partial/incomplete-answers, раздел 9 п.3) — синхронный, без job'а.

---

## 9. API кандидатов

Base: `/api/v1/...` (DRF router, `sfera_backend/sfera_backend/api/urls.py`).

| METHOD | URL | View (file:line) | Назначение |
|---|---|---|---|
| GET | `/api/v1/courses/{course_uuid}/applications/` | `CourseCandidatesViewSet.list` — `courses/views.py:284-317` | Список кандидатов курса; `CourseCandidateListRowSerializer` — id, record_type, progress, status, candidate_email/name, source, hh_* |
| GET/PATCH | `/api/v1/courses/{course_uuid}/applications/{id}/` | `CourseCandidatesViewSet` (Retrieve/Update) | Деталь кандидата; `CourseCandidateDetailSerializer` |
| GET | `/api/v1/courses/{course_uuid}/candidates/{candidate_id}/answers/` | `CandidateCourseAnswersListView` — `testchecks/views.py:543-616` | Все ответы кандидата одним запросом (дерево lesson→test→attempt→answer) |
| GET | `/api/v1/courses/{course_uuid}/candidates/completed-answers/` | `CompletedCandidatesAnswersView` (~`views.py:494`) | CSV-подобная выгрузка 100% |
| GET | `/api/v1/courses/{course_uuid}/candidates/partial-answers/` | `PartialCandidatesAnswersView` — `views.py:514-530` | Выгрузка 75-99% |
| GET | `/api/v1/courses/{course_uuid}/candidates/incomplete-answers/` | `IncompleteCandidatesAnswersView` — `views.py:534-550` | Выгрузка 0-74% |
| GET | `/api/v1/companies/{slug}/integrations/hh/negotiations/{pk}/resume.pdf/` | `HHResumePdfView` — `integrations/headhunter/views.py:157-195` | PDF HH-резюме по `hh_negotiation_pk`, проксирует HH API "на лету" |
| GET/POST | `/api/v1/tests/{test_id}/attempts/` | `TestAttemptViewSet` — `testchecks/views.py:192-249` | Список/создание попыток |
| GET | `/api/v1/tests/attempts/{attempt_id}/` | `TestAttemptRetrieveView:253-266` | Одна попытка с ответами |
| POST | `/api/v1/attempts/{attempt_id}/questions/{question_id}/answer/` | `QuestionAnswerView` | Сохранить ответ |
| POST | `/api/v1/courses/{course_uuid}/candidates/resume-video-archive/` | `CandidateArchiveJobCreateView:562-624` | Создать job ZIP-архива (min_score/max_score) |
| GET | `/api/v1/courses/{course_uuid}/candidates/resume-video-archive/{job_id}/` | `CandidateArchiveJobDetailView:632-647` | Статус job'а |
| GET | `/api/v1/candidate-archive-jobs/` | `CandidateArchiveJobListView:700+` | Все job'ы компании |
| GET | `/api/v1/companies/{slug}/integrations/hh/negotiations/` | `HHNegotiationsView` — `integrations/headhunter/views.py:413-490` | Список HH-лидов, фильтры vacancy_id/status/stage/search |
| GET | `/api/v1/my-courses/` | `CandidateCoursesView` | Курсы кандидата (со стороны кандидата) |

**НЕТ ПОДХОДЯЩЕГО ENDPOINT**: прямого `GET /candidates/{candidate_id}/video/` или агрегированного "полный профиль кандидата" (резюме+видео+ответы+прогресс одним вызовом, по стабильному candidate_id, без привязки к конкретному course_uuid в URL) — не существует. Собирать профиль под AI-модуль придётся из нескольких вызовов/сервисов, либо (что эффективнее) — переиспользовать Django-сервисные функции напрямую (см. раздел 8, `collect_candidate_archive_entries`) без похода через HTTP.

---

## 10. Определение изменений

| Источник | Есть updated_at? | Можно определить конкретное изменение? |
|---|---|---|
| `Application` | Да (`CreatedModifiedBaseModel`) | Да — `updated_at` меняется при смене статуса/комментария |
| `Progress` | Да | Да — `updated_at`, `completed_at`, `completed_lessons` растут монотонно |
| `Answer` (ответы, резюме-файл, видео) | Да (`created_at`/`modified_at`) + `answered_at` | Да, и надёжнее чем везде: ответы **неперезаписываемы** после финализации (`UniqueConstraint`), значит новая запись = новое событие, старые никогда не "тихо" меняются |
| `AnswerVideoUpload` | Да | Промежуточное состояние до финализации, не нужен для detection после того как Answer создан |
| `CustomUser` (кандидат) | **Нет** created_at/updated_at | Появление нового кандидата детектируется косвенно — через появление его первого `Application` |
| `HHNegotiationRecord` | Да (`CreatedModifiedBaseModel`) | Да, включая `processed_at`, `applied_status` |

Version/hash/event log/audit log в общем виде — **не найдено** как общий механизм. Есть частные журналы: `IntegrationEvent` (HH-события), `CandidateMergeLog`, `DataDeletionLog` — не покрывают "изменение резюме/ответа/прогресса" как единый event log.

**Webhook**: только входящий, от HH (`HHWebhookView`, `AllowAny`, без проверки подписи — доверие через employer_id + идемпотентность по `webhook-send-id`). Исходящих webhook'ов (для уведомления внешнего AI-модуля о новых кандидатах) — нет.

**Вывод**: change detection **можно построить без изменения архитектуры** — на `updated_at` полей `Application`/`Progress` + факте появления новых `Answer` (по `id`/`answered_at` после `MAX(id)` с прошлого прогона) + сравнении `progress_score`. Единственное слабое место — `CustomUser` без `updated_at`, но для целей AI-модуля важен не сам User, а его `Application`/`Progress`/`Answer`, которые все версионированы.

---

## 11. Фоновые процессы — что переиспользовать

- Celery/Redis/RabbitMQ/n8n — **нет**.
- Единственный работающий планировщик — **APScheduler**, уже несёт ~12 задач с разной периодичностью (от 15 сек до раз в сутки), включая ровно такой же паттерн "polling job processing", какой нужен AI-модулю ("несколько раз в день проверять изменения").
- **Прямая рекомендация**: добавить job AI-анализа в тот же `core/scheduler.py` по образцу `process_candidate_archive_jobs` — тот же `BackgroundScheduler`, свой `interval`/`cron`, свой `max_instances=1`, свой сервис-модуль в стиле `candidate_archive_job_processing.py`. Это единственный принятый в проекте паттерн — сознательно выбран разработчиками (задокументирован явным комментарием "не заводим отдельный процесс, переиспользуем APScheduler").
- Отдельный Docker-сервис `scheduler` уже развёрнут и живёт постоянно — AI-джобу можно добавить туда же без нового деплой-юнита.
- Management command (`python manage.py xxx`) — альтернативный паттерн для ручного/разового запуска (используется для `hh_import`, `hh_autosort` вручную), полезен для первого backfill-прогона AI-анализа по всей базе.

---

## 12. Что НЕ стоит трогать

Критичные существующие потоки, куда AI-модуль не должен вмешиваться:

- **Прохождение демонстрации и ответы**: `TestAttemptViewSet`, `QuestionAnswerView`, `Answer`/`AnswerVideoUpload` lifecycle (`testchecks/`) — любое изменение схемы `Answer`/`TestAttempt` рискует сломать уже работающий (и уже переживший несколько раундов багфиксов, судя по памяти проекта) поток прохождения. AI-модуль должен **только читать**, никогда не писать в эти таблицы.
- **`Progress`/расчёт процента** — формула продублирована в двух местах (сериализатор + архивный сервис); НЕ добавлять третье место со своей копией формулы — переиспользовать существующую логику или явно вынести её в общую функцию, если она понадобится AI-модулю (риск рассинхронизации).
- **HH-интеграция целиком** (`integrations/headhunter/`) — OAuth-токены, webhook-приёмник, autosort, message delivery — по памяти проекта это область с историей нетривиальных багов (`project_hh_message_delivery_bug`, `project_hh_autosort_redesign`). Не переиспользовать HH-токены/клиент напрямую из AI-модуля — только через существующий `services.get_resume_pdf`/аналогичные публичные функции, не трогая внутренний state коннекта.
- **CandidateArchiveJob / ZIP-экспорт** — переиспользовать его *сервисные функции* (раздел 8) можно и нужно, но не сам job/APScheduler-слот — не делить `max_instances=1` слот с этим job'ом, у AI-анализа должен быть свой независимый job с своим расписанием.
- **Существующие CSV-экспорты** (completed/partial/incomplete-answers) — оставить как есть, у HR уже есть привычный воркфлоу вокруг них.
- **Авторизация кандидата** (JWT, `registration_uuid`/`enrollment_token` флоу) — не трогать, AI-модуль работает от имени backend-сервиса/админа, не от кандидата.

---

## 13. Сводная карта

| Данные | Где хранятся | Связь с candidate_id | Есть updated_at | Можно определить изменение | Можно использовать для AI |
|---|---|---|---|---|---|
| Candidate (User) | `users_customuser`, `CustomUser` | это и есть PK | Нет (только `date_joined`) | Косвенно, через Application | Да — как identity anchor |
| Vacancy/Course | `courses_course` + `VacancyCourseMapping` (HH) | через `Application.course` | Да | Да | Да |
| Application | `courses_application` | `Application.candidate` FK | Да | Да (status/comment) | Да — основной "hub" |
| Resume (анкетное) | `testchecks_answer.file` (S3/local) | через `attempt.candidate` | Да (`answered_at`) | Да, неперезаписываемо | Да, но нужен парсинг текста |
| Resume (HH) | не хранится, только `hh_resume_id` в `HHNegotiationRecord` | через `application.hh_negotiation` | Да (record) | Да | Да, но требует live-запроса к HH API за PDF |
| Answers | `testchecks_answer` (реляционно) | `answer.attempt.candidate` | Да | Да, надёжно (immutable) | Да — прямой источник |
| Video (визитка/ответы) | S3 `answer_video/...`, ключ в `Answer.file` | через `attempt.candidate` | Да | Да, надёжно | Да, но нужна транскрибация (не реализована) |
| Demo progress | вычисляется из `Progress` (`courses_progress`) | `Progress.candidate` FK | Да | Да | Да |

---

## Что уже готово для AI-модуля

- Стабильный `candidate_id` = `CustomUser.id`, пронизывает все нужные таблицы через FK.
- Реляционные, не-JSON ответы (`Answer`) с иммутабельностью после финализации — идеальная основа для "не обрабатывать повторно неизменившееся".
- Готовые Django-сервисные функции сбора данных по диапазону прогресса без ZIP (`courses/candidates_archive_service.py::collect_candidate_archive_entries`, `courses/completed_candidate_answers.py::build_archive_candidates_answers`) — можно вызывать напрямую из нового AI-сервиса, минуя HTTP и минуя архивацию.
- Единый принятый паттерн фоновых задач (APScheduler) — не нужно вводить новую инфраструктуру (Celery/Redis) для периодического запуска анализа.
- `updated_at`/`created_at`/`answered_at` есть почти везде, где нужно, кроме самого `CustomUser`.
- Есть уже согласованный (хоть и не реализованный) план транскрибации видео (`project-context/candidate-video-transcription/`) — стек и решения там совместимы с задачей AI-анализа, стоит проектировать AI-модуль вместе с ним, а не отдельно.

## Чего не хватает

- Модели `CandidateProfile` (агрегированного снепшота) и `VacancyProfile` (структурированных требований заказчика) — нет, придётся создавать с нуля.
- Извлечённого текста резюме (ни анкетного, ни HH) — нет; нужен парсинг PDF/DOC при первом обращении к AI-модулю.
- Транскрипции видео — нет, реализация не начата (план есть).
- Общей функции расчёта `progress_score` — сейчас продублирована в двух местах; желательно вынести в общий helper перед тем, как на неё будет опираться третий потребитель (AI-модуль).
- Endpoint/сервиса "полный профиль кандидата одним вызовом" — нет, нужно собирать из нескольких источников.
- Модели `AIAnalysisResult`/`CandidateFitScore` с версионированием и полем "на основе какого снепшота данных посчитано" — нет, это ядро нового модуля.
- Механизма определения "у кандидата появились новые данные с прошлого анализа" как готовой абстракции — сейчас это нужно строить вручную поверх существующих `updated_at`, но строительный материал весь на месте.

## Минимальные изменения

Для цепочки `Candidate Data → Candidate Profile → Vacancy Fit → сохранённый AI-анализ` с инкрементальностью:

1. Новые модели (новое Django-приложение, например `ai_analysis/`, не трогающее существующие apps):
   - `VacancyProfile` — FK на `Course` (=вакансия/демо), структурированные требования (JSON или отдельные поля), заполняется вручную/через отдельный UI.
   - `CandidateAnalysis` — FK на `Application` (не на `CustomUser` напрямую — так анализ автоматически привязан к конкретной вакансии/курсу), поля: `fit_score`, `confidence`/`data_completeness`, `strengths`/`risks`/`gaps` (JSON), `reasoning` (текст), `recommendation`, `interview_questions` (JSON), `analyzed_at`, и **снепшот версии входных данных** — например хэш или просто набор меток времени (`application.updated_at`, `progress.updated_at`, максимальный `answer.created_at`, наличие/отсутствие видео) на момент анализа — это и есть механизм "не переанализировать неизменившееся".
   - `ResumeExtract` (или поле в `CandidateAnalysis`) — кэш извлечённого текста резюме, привязан к конкретному `Answer.id`/файлу, чтобы не парсить повторно один и тот же файл.
   - `VideoTranscript` — по аналогии с планом `candidate-video-transcription/`, кэш транскрипта по `Answer.id` видео.
2. Новый APScheduler-job в `core/scheduler.py` (по образцу `process_candidate_archive_jobs`) — раз в N часов проходит по всем `Application`, у которых `updated_at`/связанные `Progress.updated_at`/`MAX(Answer.created_at по attempt.candidate)` новее, чем снепшот последнего `CandidateAnalysis`, — и ставит их в очередь на (пере)анализ.
3. Сервисный слой сбора `CandidateProfile` — новый модуль, переиспользующий `collect_candidate_archive_entries`-подобную логику (без ZIP) + сериализатор ответов (`CandidateCourseAnswersLessonsSerializer`-подобный) + резюме (парсинг файла/запрос HH PDF) + транскрипт видео (если есть).
4. Ничего в существующих моделях `Answer`/`Application`/`Progress`/`CustomUser` менять не нужно — всё нужное для detection уже есть как read-only источник.

## Риски

- **`CustomUser` без `updated_at`** — если в будущем понадобится детектировать изменения самого профиля кандидата (не через Application) — придётся добавлять поле (миграция в чужую критичную модель, делать очень аккуратно).
- **Дублирование формулы progress** (раздел 7, 12) — если AI-модуль скопирует её в третий раз, будущий рефакторинг легко пропустит одно из трёх мест.
- **HH-резюме не кэшируется** — каждый показ PDF идёт живым запросом к HH API; если AI-модуль будет дергать `get_resume_pdf` для сотен кандидатов при первом backfill — риск упереться в rate-limit HH API. Нужно кэшировать извлечённый текст после первого парсинга (см. "минимальные изменения", `ResumeExtract`), не дергать HH повторно.
- **HH-лиды без Application** (раздел 3) — если AI должен покрывать "всех кандидатов независимо от прогресса", включая тех, кто не начал демонстрацию, у них нет `candidate_id`/`Application` — модель `CandidateAnalysis` завязанная на `Application` их не покроет; нужно отдельно решить, входят ли такие лиды в scope, и если да — заводить для них отдельную ветку (FK на `HHNegotiationRecord` вместо `Application`).
- **APScheduler — не Celery**: нет встроенной устойчивости к падению процесса посреди job'а (в отличие от персистентной очереди) — при сбое контейнера `scheduler` во время AI-анализа партии кандидатов нужна ручная идемпотентность (что при снепшот-based detection получается естественно — просто перезапустится на тех же "устаревших" кандидатах).
- **Прод-адрес backend неоднозначен** (раздел 1) — деплой нового job'а нужно направлять на актуальный контур; уточнить у владельца перед деплоем.
- **Видео-ответы не проходят модерацию/валидацию содержимого** — размер до 150МБ, без ограничения длительности; для транскрибации это может означать долгие аудио-дорожки — стоит учитывать в оценке стоимости/времени whisper-обработки.

## Рекомендуемая точка интеграции

Новое изолированное Django-приложение (например `ai_analysis/`) внутри `sfera_backend/sfera_backend/`:
- **Модели** — свои (`VacancyProfile`, `CandidateAnalysis`, `ResumeExtract`, `VideoTranscript`), никаких изменений в `users`/`courses`/`testchecks`/`lessons`/`integrations`.
- **Чтение данных** — только через существующие ORM-связи (`Application`, `Progress`, `Answer`, `HHNegotiationRecord`) и, где возможно, переиспользуя уже написанные сервисные функции сбора (раздел 8) — не через HTTP self-call, напрямую на уровне Python/ORM (быстрее, без дублирования логики авторизации).
- **Фоновый запуск** — новый job в уже существующем `core/scheduler.py`/контейнере `scheduler`, свой независимый `interval`, не разделяющий `max_instances` с другими job'ами.
- **API для UI** (если нужно показывать Fit Score в интерфейсе HR) — новый DRF ViewSet в стиле существующих (`CourseCandidatesViewSet`), новый URL-неймспейс `/api/v1/courses/{course_uuid}/candidates/{id}/ai-analysis/`, не трогающий существующие сериализаторы кандидата.

Такая интеграция гарантирует: демонстрация должности, ответы, HH-синхронизация и существующие экспорты продолжают работать полностью независимо от AI-модуля — он только читает их данные и пишет в свои собственные таблицы.
