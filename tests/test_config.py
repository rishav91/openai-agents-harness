import pytest

from equity_harness.config import ConfigError, load_settings


def test_refuses_missing_cost_bound(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_EXECUTOR_API_KEY", "sk-exec")
    monkeypatch.setenv("AGENT_MODEL", "gpt-6-astra")
    monkeypatch.delenv("COST_BOUND_USD", raising=False)
    with pytest.raises(ConfigError):
        load_settings()


def test_refuses_non_positive_cost_bound(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_EXECUTOR_API_KEY", "sk-exec")
    monkeypatch.setenv("AGENT_MODEL", "gpt-6-astra")
    monkeypatch.setenv("COST_BOUND_USD", "0")
    with pytest.raises(ConfigError):
        load_settings()


def test_loads_when_complete(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_EXECUTOR_API_KEY", "sk-exec")
    monkeypatch.setenv("AGENT_MODEL", "gpt-6-astra")
    monkeypatch.setenv("COST_BOUND_USD", "2.5")
    settings = load_settings()
    assert settings.cost_bound_usd == 2.5
    assert settings.max_research_count == 12
    assert settings.otel_service_name == "equity-harness"
