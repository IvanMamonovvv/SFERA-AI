from unittest.mock import MagicMock, patch

from sfera_ai.config import Settings
from sfera_ai.platform_db import RESUME_DETECTION_TABLES
from sfera_ai.scheduler import run_resume_retry, run_tick


def _settings() -> Settings:
    return Settings.model_construct(
        platform_database_url="postgresql+psycopg://ai_readonly:x@localhost:5433/sfera",
        write_database_url="sqlite:///:memory:",
        hh_backend_base_url="http://backend",
        hh_backend_admin_login="admin",
        hh_backend_admin_password="secret",
        hh_backend_host_header="sphera-api.ru",
        s3_endpoint_url="http://s3",
        s3_bucket="ai-bucket",
        s3_access_key="key",
        s3_secret_key="secret",
        s3_region="ru-1",
        openrouter_api_key="or-key",
        openrouter_base_url="https://openrouter.ai/api/v1",
        bff_shared_secret="shared",
        ai_processing_dry_run=True,
        ai_analysis_max_concurrent_jobs=200,
        ai_stuck_job_threshold_hours=2,
        ai_processing_pilot_course_id=None,
        resume_pii_ttl_days=90,
        resume_extract_max_attempts=5,
    )


@patch("sfera_ai.scheduler.process_batch")
@patch("sfera_ai.scheduler.detect_and_enqueue")
@patch("sfera_ai.scheduler.reflect_platform_tables")
@patch("sfera_ai.scheduler.boto3")
@patch("sfera_ai.scheduler.HHClient")
@patch("sfera_ai.scheduler.OpenRouterClient")
@patch("sfera_ai.scheduler.create_engine")
@patch("sfera_ai.scheduler.make_write_engine")
def test_run_tick_builds_hh_and_s3_clients_and_reflects_resume_tables(
    mock_make_write_engine,
    mock_create_engine,
    mock_llm_client_cls,
    mock_hh_client_cls,
    mock_boto3,
    mock_reflect,
    mock_detect_and_enqueue,
    mock_process_batch,
    tmp_engine,
):
    settings = _settings()
    mock_make_write_engine.return_value = tmp_engine
    mock_platform_base = MagicMock(name="platform_base")
    mock_reflect.return_value = mock_platform_base
    mock_hh_client = MagicMock(name="hh_client")
    mock_hh_client_cls.return_value = mock_hh_client
    mock_s3_client = MagicMock(name="s3_client")
    mock_boto3.client.return_value = mock_s3_client
    mock_detect_and_enqueue.return_value = []
    mock_process_batch.return_value = []

    run_tick(settings)

    mock_hh_client_cls.assert_called_once_with(
        base_url=settings.hh_backend_base_url,
        login=settings.hh_backend_admin_login,
        password=settings.hh_backend_admin_password,
        host_header=settings.hh_backend_host_header,
    )
    mock_boto3.client.assert_called_once_with(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    mock_reflect.assert_called_once()
    assert mock_reflect.call_args.kwargs["tables"] == RESUME_DETECTION_TABLES

    mock_detect_and_enqueue.assert_called_once()
    assert mock_detect_and_enqueue.call_args.args[1] is mock_platform_base

    mock_process_batch.assert_called_once()
    process_batch_kwargs = mock_process_batch.call_args.kwargs
    assert process_batch_kwargs["hh_client"] is mock_hh_client
    assert process_batch_kwargs["s3_client"] is mock_s3_client
    assert process_batch_kwargs["s3_bucket"] == settings.s3_bucket


@patch("sfera_ai.scheduler.requeue_failed_resumes")
@patch("sfera_ai.scheduler.reflect_platform_tables")
@patch("sfera_ai.scheduler.boto3")
@patch("sfera_ai.scheduler.HHClient")
@patch("sfera_ai.scheduler.OpenRouterClient")
@patch("sfera_ai.scheduler.create_engine")
@patch("sfera_ai.scheduler.make_write_engine")
def test_run_resume_retry_builds_clients_and_passes_max_attempts(
    mock_make_write_engine,
    mock_create_engine,
    mock_llm_client_cls,
    mock_hh_client_cls,
    mock_boto3,
    mock_reflect,
    mock_requeue_failed_resumes,
    tmp_engine,
):
    settings = _settings()
    mock_make_write_engine.return_value = tmp_engine
    mock_platform_base = MagicMock(name="platform_base")
    mock_reflect.return_value = mock_platform_base
    mock_hh_client = MagicMock(name="hh_client")
    mock_hh_client_cls.return_value = mock_hh_client
    mock_s3_client = MagicMock(name="s3_client")
    mock_boto3.client.return_value = mock_s3_client
    mock_requeue_failed_resumes.return_value = []

    run_resume_retry(settings)

    mock_requeue_failed_resumes.assert_called_once()
    kwargs = mock_requeue_failed_resumes.call_args.kwargs
    assert kwargs["hh_client"] is mock_hh_client
    assert kwargs["s3_client"] is mock_s3_client
    assert kwargs["s3_bucket"] == settings.s3_bucket
    assert kwargs["max_attempts"] == settings.resume_extract_max_attempts
    assert mock_requeue_failed_resumes.call_args.args[1] is mock_platform_base
