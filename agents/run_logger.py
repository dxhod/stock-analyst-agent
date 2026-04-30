from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = Path(os.getenv("AGENT_LOG_DIR", PROJECT_ROOT / "logs"))
LOG_FILE = LOG_DIR / "agent_runs.jsonl"


def ensure_run_id(state: dict[str, Any]) -> str:
    run_id = state.get("run_id")
    if run_id:
        return str(run_id)
    run_id = str(uuid4())
    state["run_id"] = run_id
    return run_id


def log_agent_run(
    *,
    agent: str,
    model: str,
    prompt: str,
    output: str,
    state: dict[str, Any] | None = None,
) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    state = state or {}
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": state.get("run_id"),
        "agent": agent,
        "model": model,
        "ticker": state.get("ticker"),
        "tickers": state.get("tickers"),
        "language": state.get("language"),
        "user_query": state.get("user_query"),
        "input": prompt,
        "output": output,
    }
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
