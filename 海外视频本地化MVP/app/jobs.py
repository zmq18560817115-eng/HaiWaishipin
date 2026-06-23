"""后台运行 pipeline 子命令（fetch / decompose 等）。"""

from __future__ import annotations

import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MVP_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = MVP_ROOT / "scripts" / "pipeline.py"
PYTHON = MVP_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

_lock = threading.Lock()
_state: dict[str, Any] = {
    "status": "idle",
    "job": "",
    "started_at": None,
    "finished_at": None,
    "exit_code": None,
    "output": "",
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def job_status() -> dict[str, Any]:
    with _lock:
        return dict(_state)


def _set(**kwargs: Any) -> None:
    with _lock:
        _state.update(kwargs)


def _run_pipeline(args: list[str]) -> None:
    job_name = args[0] if args else "unknown"
    _set(status="running", job=job_name, started_at=_utc(), finished_at=None, exit_code=None, output="")
    cmd = [str(PYTHON), str(PIPELINE), *args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(MVP_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        _set(
            status="done" if proc.returncode == 0 else "error",
            finished_at=_utc(),
            exit_code=proc.returncode,
            output=output[-12000:],
        )
    except Exception as exc:  # noqa: BLE001
        _set(status="error", finished_at=_utc(), exit_code=-1, output=str(exc))


def start_job(name: str, *, engine: str = "auto") -> dict[str, Any]:
    allowed = {"links", "fetch", "decompose", "templates", "products"}
    if name not in allowed:
        raise ValueError(f"不支持的任务: {name}")
    with _lock:
        if _state.get("status") == "running":
            raise RuntimeError(f"已有任务进行中: {_state.get('job')}")
    args = [name]
    if name == "fetch":
        args.extend(["--engine", engine])
    thread = threading.Thread(target=_run_pipeline, args=(args,), daemon=True)
    thread.start()
    return job_status()
