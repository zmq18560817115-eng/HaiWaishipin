from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import settings


def _all_search_roots() -> list[Path]:
    roots = [root for root in settings.knowledge_roots if root.exists()]
    nas_root = Path(r"\\DS223\obsidian知识库")
    if nas_root.exists() and nas_root not in roots:
        roots.append(nas_root)
    return roots


def _fallback_search(query: str, limit: int) -> list[dict[str, Any]]:
    terms = [term.lower() for term in query.split() if term.strip()]
    results: list[dict[str, Any]] = []
    for root in _all_search_roots():
        for path in root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            lower = text.lower()
            score = sum(lower.count(term) for term in terms)
            if not score:
                continue
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            snippet = next(
                (line for line in lines if any(term in line.lower() for term in terms)),
                lines[0] if lines else "",
            )
            results.append(
                {
                    "source_id": "portable-fallback",
                    "path": str(path),
                    "relative_path": path.name,
                    "title": path.stem,
                    "score": float(score),
                    "matched_terms": [term for term in terms if term in lower],
                    "snippet": snippet[:800],
                    "metadata": {},
                }
            )
    return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]


def search_knowledge(query: str, limit: int = 6) -> dict[str, Any]:
    script = settings.resolved_kro_script
    roots = _all_search_roots()
    config_path = settings.kro_config_path
    if config_path:
        resolved_config = Path(config_path)
        if not resolved_config.is_absolute():
            resolved_config = settings.base_dir / resolved_config
        if resolved_config.exists():
            config_path = str(resolved_config)
        else:
            config_path = ""
    if script.exists():
        command = [
            sys.executable,
            str(script),
            query,
            "--limit",
            str(limit),
            "--json",
        ]
        for root in roots:
            command.extend(["--root", str(root)])
        if settings.kro_config_path:
            command.extend(["--config", config_path])
        try:
            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                env=child_env,
                timeout=120,
                check=True,
            )
            payload = json.loads(completed.stdout or "{}")
            if "results" not in payload:
                raise json.JSONDecodeError("missing results", completed.stdout or "", 0)
            payload["engine"] = "knowledge-research-orchestrator"
            return payload
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError, UnicodeError):
            pass
    results = _fallback_search(query, limit)
    return {
        "query": query,
        "result_count": len(results),
        "results": results,
        "engine": "portable-fallback",
    }


def context_text(payload: dict[str, Any]) -> str:
    chunks = []
    for index, item in enumerate(payload.get("results", []), start=1):
        chunks.append(
            f"[K{index}] {item.get('title') or item.get('relative_path')}\n"
            f"Source: {item.get('path')}\n"
            f"Evidence: {item.get('snippet', '')}"
        )
    return "\n\n".join(chunks) or "No company knowledge evidence was retrieved."
