from __future__ import annotations

import asyncio
import uuid
from contextlib import suppress
from pathlib import Path

from openai import AsyncOpenAI

from equity_harness.config import Settings
from equity_harness.docker_sandbox import (
    build_image,
    ensure_running,
    remove_container,
    start_executor,
)

CONNECT_TIMEOUT_SECONDS = 180.0


async def create_self_hosted_session(client: AsyncOpenAI, settings: Settings):
    session = await client.beta.agents.sessions.create(
        agent={
            "model": settings.agent_model,
            "instructions": (
                "Phase 0 skeleton: do not research equities. "
                "Wait for later input. Do not invent a brief."
            ),
        },
        environment={
            "type": "self_hosted",
            "workspace_directory": settings.workspace_in_container,
        },
    )
    env = session.environment
    if getattr(env, "type", None) != "self_hosted":
        raise RuntimeError(f"expected self_hosted environment, got {env}")
    return session


async def wait_until_connected(events, container_name: str) -> None:
    async with asyncio.timeout(CONNECT_TIMEOUT_SECONDS):
        async for event in events:
            await asyncio.to_thread(ensure_running, container_name)
            event_type = getattr(event, "type", None)
            if event_type == "agent.session.environment.connected":
                print("environment connected")
                return
            if event_type == "agent.session.environment.failed":
                error = getattr(getattr(event, "environment", None), "error", None)
                raise RuntimeError(f"environment failed: {error}")
            if event_type in {"agent.session.failed", "error"}:
                raise RuntimeError(f"session failed during connect: {event}")
    raise RuntimeError("event stream ended before environment.connected")


async def connect_sandbox(
    settings: Settings,
    host_workspace: Path,
) -> tuple[str, str, AsyncOpenAI]:
    """Create session, start Docker exec-server, wait for connected.

    Opens the event stream before the executor so connect events are not missed.
    Does not send a research brief (Phase 0).
    Caller must close the client, remove the container, and optionally delete the session.
    """
    container_name = f"equity-harness-{uuid.uuid4().hex[:12]}"
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    session = None
    try:
        await asyncio.to_thread(build_image, settings.docker_image)
        session = await create_self_hosted_session(client, settings)
        print(f"created session {session.id}")
        print(f"environment id: {session.environment.id}")
        async with client.beta.agents.sessions.stream(session.id) as events:
            await asyncio.to_thread(
                start_executor,
                image=settings.docker_image,
                container_name=container_name,
                executor_api_key=settings.executor_api_key,
                environment_id=session.environment.id,
                remote_url=session.environment.remote_url,
                host_workspace=host_workspace,
                workspace_in_container=settings.workspace_in_container,
            )
            await wait_until_connected(events, container_name)
        return session.id, container_name, client
    except Exception:
        remove_container(container_name)
        if session is not None:
            with suppress(Exception):
                await client.beta.agents.sessions.delete(session.id)
        await client.close()
        raise
