from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MAX_RESEARCH = 12
DEFAULT_IMAGE = "equity-harness-sandbox:latest"


class ConfigError(SystemExit):
    """Process must not start (FR-1.6)."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    executor_api_key: str
    cost_bound_usd: float
    agent_model: str
    max_research_count: int
    runs_dir: Path
    docker_image: str
    otel_endpoint: str
    otel_service_name: str
    workspace_in_container: str = "/workspace"


def load_settings() -> Settings:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    executor = os.environ.get("OPENAI_EXECUTOR_API_KEY", "").strip()
    model = os.environ.get("AGENT_MODEL", "").strip()
    bound_raw = os.environ.get("COST_BOUND_USD", "").strip()
    max_raw = os.environ.get("MAX_RESEARCH_COUNT", str(DEFAULT_MAX_RESEARCH)).strip()
    runs = Path(os.environ.get("RUNS_DIR", "runs")).resolve()
    image = os.environ.get("DOCKER_IMAGE", DEFAULT_IMAGE).strip()
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    otel_service = os.environ.get("OTEL_SERVICE_NAME", "equity-harness").strip() or "equity-harness"

    missing: list[str] = []
    if not api_key:
        missing.append("OPENAI_API_KEY")
    if not executor:
        missing.append("OPENAI_EXECUTOR_API_KEY")
    if not model:
        missing.append("AGENT_MODEL")
    if not bound_raw:
        missing.append("COST_BOUND_USD")
    if missing:
        raise ConfigError(
            "Missing required env vars: "
            + ", ".join(missing)
            + ". Copy .env.example to .env. COST_BOUND_USD is never prompted (FR-1.6)."
        )

    try:
        bound = float(bound_raw)
    except ValueError as exc:
        raise ConfigError("COST_BOUND_USD must be a number greater than 0.") from exc
    if bound <= 0:
        raise ConfigError("COST_BOUND_USD must be greater than 0 (FR-1.6).")

    try:
        max_research = int(max_raw)
    except ValueError as exc:
        raise ConfigError("MAX_RESEARCH_COUNT must be an integer.") from exc
    if max_research < 1:
        raise ConfigError("MAX_RESEARCH_COUNT must be >= 1.")

    return Settings(
        openai_api_key=api_key,
        executor_api_key=executor,
        cost_bound_usd=bound,
        agent_model=model,
        max_research_count=max_research,
        runs_dir=runs,
        docker_image=image,
        otel_endpoint=otel_endpoint,
        otel_service_name=otel_service,
    )
