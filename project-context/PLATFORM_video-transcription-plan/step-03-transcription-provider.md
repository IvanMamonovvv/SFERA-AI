# Step 03 — TranscriptionProvider (whisper) + env-переключатель

**Статус:** 🟡 Код готов, живой прогон — на step-09
**Зависит от:** step-00 (выбор модели).
**Цель:** абстракция «видео → текст» с реализацией self-hosted faster-whisper и возможностью переключить на cloud одной env.

## Интерфейс

```python
# testchecks/services/transcription/base.py
class TranscriptionResult(NamedTuple):
    text: str
    is_empty: bool          # речь не распознана / тишина
    language: str | None
    duration_sec: float | None

class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: str) -> TranscriptionResult: ...
```

## Реализации

### 1. LocalFasterWhisperProvider (по умолчанию)
- `WhisperModel(size, device="cpu", compute_type="int8")` — модель из step-00.
- Модель грузится **один раз на процесс воркера** (не на каждое видео) — держать синглтоном.
- `language="ru"` (можно авто-детект, но кандидаты русскоязычные → фиксируем «ru» для скорости/точности).
- `is_empty = len(text.strip()) == 0` или очень короткий/мусорный → флаг для summary (step-04).

### 2. YandexSpeechKitProvider (fallback/рубильник)
- REST к Yandex Cloud STT, оплата в РФ, без прокси. Для пиков/завалов.

### 3. ProxyWhisperProvider (fallback)
- OpenAI whisper-1 через proxyapi.ru/vsegpt (РФ-прокси), оплата в рублях.

## Извлечение аудио (перед провайдером)

Видео из S3/диска → временный wav:
```
ffmpeg -i input.mp4 -vn -ac 1 -ar 16000 -f wav output.wav
```
- `-vn` без видео, моно, 16 кГц — то, что нужно whisper, меньше размер.
- Читать исходник через storage-API (`answer.file.open()`) во временный файл (работает и с S3, и с диском — см. 02_CONTEXT).
- Паттерн запуска ffmpeg/ffprobe — как в `lessons/services/video_processing.py`.

## Выбор провайдера

```python
# по env, без изменения кода воркера
TRANSCRIBE_PROVIDER = env('TRANSCRIBE_PROVIDER', default='local')  # local | yandex | proxy
```
Фабрика возвращает нужный провайдер. **Это и есть «рубильник»** — при росте нагрузки меняем одну переменную.

## Крайние случаи

- Битый/пустой/0-секундный файл → ffmpeg вернёт ошибку или пустой wav → `is_empty=True`, не падаем.
- Видео без аудиодорожки (кандидат закрыл камеру, но и звука нет) → `is_empty=True`.
- Очень длинное видео → whisper справится, но логировать время (для мониторинга).

## Критерий готовности

- [ ] `local` провайдер транскрибирует тестовое русское видео в текст.
      (Код готов, faster-whisper не установлен локально — реальный прогон
      перенесён на step-09-tests-smoke.md.)
- [x] Пустое/тихое видео → `is_empty=True`, без исключений (ffmpeg-ошибка,
      0-байтовый wav и пустой текст — все три ветки обработаны в
      `transcribe_video`, без реального видео проверено только по коду).
- [x] Переключение `TRANSCRIBE_PROVIDER` меняет бэкенд без правок воркера
      (`get_transcription_provider()` — фабрика по env; `yandex`/`proxy` пока
      `NotImplementedError`, не в объёме этого шага — решение владельца).
- [x] Временные файлы удаляются после обработки (`finally: os.remove`,
      нет утечки диска — по коду, реальный прогон не делался).

## Журнал
- `2026-09-07` — реализован `sfera_backend/testchecks/services/transcription/base.py`:
  `TranscriptionResult`, `TranscriptionProvider` Protocol, `LocalFasterWhisperProvider`
  (модель-синглтон на класс, `language=ru`, `WHISPER_MODEL_SIZE` из env, default `small`
  — решение step-00), `extract_audio_wav` (ffmpeg-паттерн из
  `lessons/services/video_processing.py`), `transcribe_video` (оркестрация:
  извлечение аудио во временный wav → провайдер → удаление wav в `finally`) и
  `get_transcription_provider()` — фабрика по `TRANSCRIBE_PROVIDER` (default `local`;
  `yandex`/`proxy` — `NotImplementedError`, вне объёма этого шага). Добавлена
  зависимость `faster-whisper==1.1.1` в `requirements.txt`. `ruff check` чисто.
  Пакет не установлен в `.venv` (тяжёлая установка с torch) — живой прогон на
  тестовом видео перенесён на step-09-tests-smoke.md.
