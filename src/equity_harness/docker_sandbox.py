from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

DOCKERFILE_DIR = Path(__file__).resolve().parents[2] / "docker"
DEFAULT_IMAGE = "equity-harness-sandbox:latest"
BUILD_TIMEOUT = 240.0
START_TIMEOUT = 30.0
HEALTH_TIMEOUT = 5.0
CLEANUP_TIMEOUT = 10.0


class DockerError(RuntimeError):
    pass


def _run(command: list[str], *, env: dict[str, str] | None = None, timeout: float) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise DockerError(
            f"Command exceeded {timeout:g}s: {shlex.join(command)}"
        ) from exc
    if result.returncode != 0:
        raise DockerError(f"Command failed: {shlex.join(command)}\n{result.stdout}")
    return result.stdout.strip()


def ensure_docker() -> None:
    if shutil.which("docker") is None:
        raise DockerError("Docker CLI is not installed or not on PATH.")


def build_image(image: str = DEFAULT_IMAGE) -> None:
    ensure_docker()
    if not (DOCKERFILE_DIR / "Dockerfile").is_file():
        raise DockerError(f"Missing Dockerfile at {DOCKERFILE_DIR}")
    command = ["docker", "build", "--tag", image, str(DOCKERFILE_DIR)]
    print(f"building image: {shlex.join(command)}")
    out = _run(command, timeout=BUILD_TIMEOUT)
    if out:
        print(out)


def start_executor(
    *,
    image: str,
    container_name: str,
    executor_api_key: str,
    environment_id: str,
    remote_url: str,
    host_workspace: Path,
    workspace_in_container: str = "/workspace",
) -> str:
    ensure_docker()
    host_workspace.mkdir(parents=True, exist_ok=True)
    command = [
        "docker",
        "run",
        "--detach",
        "--rm",
        "--name",
        container_name,
        "--init",
        "-e",
        "CODEX_API_KEY",
        "-v",
        f"{host_workspace.resolve()}:{workspace_in_container}",
        image,
        "codex",
        "exec-server",
        "--remote",
        remote_url,
        "--environment-id",
        environment_id,
    ]
    print(f"starting exec-server: {shlex.join(command)}")
    env = os.environ.copy()
    env["CODEX_API_KEY"] = executor_api_key
    try:
        container_id = _run(command, env=env, timeout=START_TIMEOUT)
    except DockerError:
        remove_container(container_name)
        raise
    print(f"started container {container_id[:12]}")
    return container_name


def ensure_running(container_name: str) -> None:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=HEALTH_TIMEOUT,
    )
    if result.returncode == 0 and result.stdout.strip() == "true":
        return
    logs = subprocess.run(
        ["docker", "logs", "--tail", "80", container_name],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=HEALTH_TIMEOUT,
    ).stdout
    raise DockerError(f"Sandbox {container_name} is not running:\n{logs}")


def remove_container(container_name: str) -> None:
    result = subprocess.run(
        ["docker", "rm", "-f", container_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=CLEANUP_TIMEOUT,
    )
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or "").strip()
    if re.fullmatch(
        r"(?:error response from daemon:\s*|error:\s*)?"
        r"no such (?:container|object):\s*['\"]?"
        + re.escape(container_name)
        + r"['\"]?",
        detail,
        flags=re.IGNORECASE,
    ):
        return
    raise DockerError(
        f"Could not remove {container_name} (exit {result.returncode}): {detail or 'no output'}"
    )
