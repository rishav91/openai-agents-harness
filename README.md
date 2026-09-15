# Equity research harness

Local OpenAI **Agents API** CLI with a **self-hosted Docker** sandbox. Design: [`docs/README.md`](docs/README.md).

**Phase 0 (this tree):** env gates, complete brief intake, session create, `codex exec-server` connect. **Does not** run universe search or subagents.

## Setup

1. Docker Desktop (or Docker Engine) running.
2. Application API key: `api.agents.read`, `api.agents.write`, `api.responses.write`.
3. Separate **environment key** from [Agents → environments keys](https://platform.openai.com/agents?tab=environments&environment_view=keys) (`OPENAI_EXECUTOR_API_KEY`). Same org/project/owner. Other permissions **None**.
4. Copy env and set `COST_BOUND_USD` (required, never prompted):

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
# Brief + env only (no API, no Docker)
equity-harness --intake-only

# Full Phase 0: session + Docker connect, then cleanup. No research message.
equity-harness
```

First connect builds `equity-harness-sandbox:latest` from [`docker/Dockerfile`](docker/Dockerfile) (`@openai/codex@alpha`).

## Traces (Jaeger)

```bash
docker compose -f observability/docker-compose.yml up -d
# set in .env: OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
equity-harness --intake-only
# open http://127.0.0.1:16686  → service equity-harness
```

If the endpoint is unset, the CLI still runs and does not export. Prometheus scrape of the CLI is not used (`ADR-007`).

## Tests

```bash
pytest
```
