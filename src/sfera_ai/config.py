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
