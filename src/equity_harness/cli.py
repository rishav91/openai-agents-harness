from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from contextlib import suppress
from pathlib import Path

from opentelemetry import trace

from equity_harness.brief import collect_brief
from equity_harness.config import load_settings
from equity_harness.docker_sandbox import remove_container
from equity_harness.session import connect_sandbox
from equity_harness.telemetry import setup_telemetry, shutdown_telemetry


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Equity research harness. Phase 0: collect a complete brief, "
            "create a self-hosted Agents API session, connect Docker exec-server. "
            "Does not start universe search or subagents."
        )
    )
    parser.add_argument(
        "--intake-only",
        action="store_true",
        help="Validate env + brief only; do not create a session or start Docker.",
    )
    return parser.parse_args(argv)


async def _phase0_connect(settings, brief, tracer) -> None:
    host_workspace = Path("workspace") / "phase0"
    host_workspace.mkdir(parents=True, exist_ok=True)
    (host_workspace / "brief.json").write_text(
        json.dumps(brief.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    with tracer.start_as_current_span("session.connect") as span:
        session_id, container_name, client = await connect_sandbox(settings, host_workspace)
        span.set_attribute("session_id", session_id)
    try:
        print(
            "Phase 0 complete. Environment connected. "
            "No research input was sent (Gate)."
        )
        print(f"session_id={session_id}")
        print(f"host_workspace={host_workspace.resolve()}")
        print(f"cost_bound_usd={settings.cost_bound_usd} (env, unused until Phase 1)")
        current = trace.get_current_span()
        current.set_attribute("session_id", session_id)
        current.set_attribute("outcome", "phase0_connected")
    finally:
        remove_container(container_name)
        with suppress(Exception):
            await client.beta.agents.sessions.delete(session_id)
        await client.close()
        print("cleaned up container and session")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = load_settings()
    tracer = setup_telemetry(settings.otel_service_name)
    run_id = uuid.uuid4().hex[:12]
    try:
        with tracer.start_as_current_span("harness.run") as root:
            root.set_attribute("run_id", run_id)
            root.set_attribute("agent_model", settings.agent_model)
            root.set_attribute("cost_bound_usd", settings.cost_bound_usd)
            with tracer.start_as_current_span("brief.intake"):
                brief = collect_brief(max_research=settings.max_research_count)
            root.set_attribute("research_count", brief.research_count)
            root.set_attribute("portfolio_count", brief.portfolio_count)
            print("\nBrief accepted:")
            print(f"  country={brief.country}")
            print(f"  exchange={brief.exchange}")
            print(f"  research_count={brief.research_count}")
            print(f"  portfolio_count={brief.portfolio_count}")
            print(f"  budget_usd={brief.budget_usd}")
            if args.intake_only:
                root.set_attribute("outcome", "intake_only")
                print("\n--intake-only: not creating a session (no research).")
                return
            asyncio.run(_phase0_connect(settings, brief, tracer))
    finally:
        shutdown_telemetry()


if __name__ == "__main__":
    main()
