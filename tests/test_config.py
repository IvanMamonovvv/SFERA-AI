import os

from sfera_ai.config import Settings


def test_settings_reads_platform_database_url(monkeypatch):
    monkeypatch.setenv("PLATFORM_DATABASE_URL", "postgresql+psycopg://ai_readonly:secret@localhost:5433/sfera")
    settings = Settings()
    assert settings.platform_database_url == "postgresql+psycopg://ai_readonly:secret@localhost:5433/sfera"
