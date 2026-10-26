"""Manually trigger puzzle queue replenishment.

Run from backend/: python -m scripts.run_queue_producer [--target-days 7]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running as `python scripts/run_queue_producer.py` from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from app.core.config import get_settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.services.queue_manager import SKIPPED_LOCK_HELD, replenish_queue  # noqa: E402

get_settings.cache_clear()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replenish the daily puzzle queue")
    parser.add_argument(
        "--target-days",
        type=int,
        default=7,
        help="Number of calendar days in the assigned horizon (default: 7)",
    )
    return parser.parse_args()


def producer_exit_code(summary: dict) -> int:
    if summary.get("skipped") == SKIPPED_LOCK_HELD:
        return 0
    if summary.get("failures"):
        return 1
    return 0


async def main() -> int:
    args = parse_args()
    if args.target_days < 1:
        raise SystemExit("--target-days must be >= 1")

    try:
        async with AsyncSessionLocal() as session:
            summary = await replenish_queue(session, target_days=args.target_days)
    finally:
        await engine.dispose()

    print(json.dumps(summary, indent=2))
    return producer_exit_code(summary)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
