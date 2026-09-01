from unittest.mock import MagicMock

import httpx
import pytest

from sfera_ai.providers import LLMResult
from sfera_ai.services.vacancy_portrait import InvalidVacancyRequirementsResponse, build_vacancy_requirements


def _llm_client(content: str):
    llm_client = MagicMock()
    llm_client.complete.return_value = LLMResult(
        content=content, provider="openrouter", model="test-model",
        tokens_input=100, tokens_output=20, latency_ms=350,
    )
    return llm_client


def test_build_requirements_without_url():
    llm_client = _llm_client('{"skills": ["Python"], "experience_years": 3}')

    requirements = build_vacancy_requirements("Python-разработчик, 3 года опыта", None, llm_client=llm_client)

    assert requirements == {"skills": ["Python"], "experience_years": 3}
    assert llm_client.complete.call_count == 1


def test_build_requirements_with_url_includes_source_url(monkeypatch):
    def fake_get(url, timeout=30.0, follow_redirects=True):
        return httpx.Response(
            200, text="<html><body><script>bad</script>Вакансия: Python</body></html>",
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr("sfera_ai.services.vacancy_portrait.httpx.get", fake_get)
    llm_client = _llm_client('{"skills": ["Python"]}')

    requirements = build_vacancy_requirements(
        "Python-разработчик", "https://hh.ru/vacancy/1", llm_client=llm_client
    )

    assert requirements["source_url"] == "https://hh.ru/vacancy/1"
    assert requirements["skills"] == ["Python"]
    user_message = llm_client.complete.call_args.kwargs["messages"][1]["content"]
    assert "Вакансия: Python" in user_message


def test_fetch_url_failure_does_not_block_portrait_only_build(monkeypatch):
    def fake_get(url, timeout=30.0, follow_redirects=True):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr("sfera_ai.services.vacancy_portrait.httpx.get", fake_get)
    llm_client = _llm_client('{"skills": ["Python"]}')

    requirements = build_vacancy_requirements(
        "Python-разработчик", "https://hh.ru/vacancy/1", llm_client=llm_client
    )

    assert requirements["skills"] == ["Python"]
    assert requirements["source_url"] == "https://hh.ru/vacancy/1"
    user_message = llm_client.complete.call_args.kwargs["messages"][1]["content"]
    assert "Описание вакансии" not in user_message


def test_invalid_json_raises_and_no_requirements_returned():
    llm_client = _llm_client("not a json")

    with pytest.raises(InvalidVacancyRequirementsResponse):
        build_vacancy_requirements("Python-разработчик", None, llm_client=llm_client)


def test_non_object_json_raises():
    llm_client = _llm_client("[1, 2, 3]")

    with pytest.raises(InvalidVacancyRequirementsResponse):
        build_vacancy_requirements("Python-разработчик", None, llm_client=llm_client)
