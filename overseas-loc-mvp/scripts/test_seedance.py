#!/usr/bin/env python3
"""测试 fal.ai SeedDance 2.0 外接是否可用。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.providers import test_seedance_connection  # noqa: E402


def main() -> int:
    result = asyncio.run(test_seedance_connection())
    print(result.get("message") or result)
    if result.get("setup"):
        print(result["setup"])
    if result.get("local_file"):
        print(f"测试视频: {result['local_file']}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
