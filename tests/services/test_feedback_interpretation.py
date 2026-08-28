from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.providers import LLMProviderError, LLMResult
from sfera_ai.services.feedback_interpretation import interpret_feedback


def _llm_result(content: str) -> LLMResult:
    return LLMResult(
        content=content, provider="openrouter", model="test-model",
        tokens_input=20, tokens_output=10, latency_ms=100,
    )


class _StubLLMClient:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.calls: list[dict] = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._result


def test_interpret_feedback_returns_llm_rule_text():
    feedback = VacancyFeedback(id=1, course_id=1, text="кандидат хорошо держится", sentiment="POSITIVE")
    client = _StubLLMClient(result=_llm_result("  Учитывать уверенную самопрезентацию как плюс.  "))

    rule = interpret_feedback(feedback, llm_client=client)

    assert rule == "Учитывать уверенную самопрезентацию как плюс."
    assert client.calls[0]["model"]
    assert client.calls[0]["prompt_version"] == "feedback-interpretation-v1"
    messages = client.calls[0]["messages"]
    assert "POSITIVE" in messages[1]["content"]
    assert "кандидат хорошо держится" in messages[1]["content"]


def test_interpret_feedback_returns_empty_string_on_llm_error():
    feedback = VacancyFeedback(id=2, course_id=1, text="фидбек", sentiment="NEGATIVE")
    client = _StubLLMClient(error=LLMProviderError("boom"))

    rule = interpret_feedback(feedback, llm_client=client)

    assert rule == ""
