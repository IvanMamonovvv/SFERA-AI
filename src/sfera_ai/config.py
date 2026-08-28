from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    platform_database_url: str
    write_database_url: str

    hh_backend_base_url: str
    hh_backend_admin_login: str
    hh_backend_admin_password: str
    hh_backend_company_slug: str
    # ALLOWED_HOSTS backend'а не включает внутреннее docker DNS-имя `backend` — только
    # публичные домены/IP. Ходим по внутренней сети (быстрее, в обход gateway), но с
    # Host-заголовком, который backend примет (найдено на реальном прогоне 2026-08-27).
    hh_backend_host_header: str = "sphera-api.ru"

    s3_endpoint_url: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str = "ru-1"

    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # 03_TDD.md, «6. Processing Queue» — снимается только для ограниченного пилота
    # (step-E6-04-queue-integration.md), по умолчанию True — реальные AI-вызовы выключены.
    ai_processing_dry_run: bool = True
    # 2026-08-27 — пересчитано под реальный объём владельца (100-200 кандидатов/сутки,
    # 3 вакансии × ~400): старое значение 5 (× 3 тика/сутки = 15/сутки) не успевало бы за
    # притоком, очередь росла бы бесконечно. 200 — на порядок с запасом относительно 200/сутки,
    # при переходе на реальный AI-вызов (E6-04) пересчитать заново по факту latency LLM.
    ai_analysis_max_concurrent_jobs: int = 200
    ai_stuck_job_threshold_hours: int = 2
    # step-E6-04-queue-integration.md, п.2 DoD — при снятом ai_processing_dry_run
    # ограничивает реальные AI-вызовы одним course (пилот), пока владелец явно не
    # расширит охват; None = без пилот-скоупинга (использовать ТОЛЬКО с dry_run=True
    # или после подтверждённого владельцем расширения пилота).
    ai_processing_pilot_course_id: int | None = None
    # step-E5-06 — TTL сырого PII резюме hh_negotiation-only лидов (не конвертировались
    # в Application); значение-заглушка, точное число — согласовать с владельцем перед прод.
    resume_pii_ttl_days: int = 90
