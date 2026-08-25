# Step 03 — TranscriptionProvider (whisper) + env-переключатель

**Статус:** ⬜ TODO
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
- [ ] Пустое/тихое видео → `is_empty=True`, без исключений.
- [ ] Переключение `TRANSCRIBE_PROVIDER` меняет бэкенд без правок воркера.
- [ ] Временные файлы удаляются после обработки (нет утечки диска).

## Журнал
- (пусто)
