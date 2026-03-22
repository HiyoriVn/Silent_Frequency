"""
Silent Frequency — action_dedupe cleanup utility

Deletes stale idempotency rows older than N days in bounded batches.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from backend.app.db.database import async_session_factory, engine
from backend.app.db.models import ActionDedupe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup old action_dedupe rows")
    parser.add_argument("--days", type=int, default=30, help="Retention window in days")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows to delete per batch")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print count, do not delete rows",
    )
    return parser.parse_args()


async def cleanup(days: int, batch_size: int, dry_run: bool) -> None:
    if days < 1:
        raise ValueError("--days must be >= 1")
    if batch_size < 1:
        raise ValueError("--batch-size must be >= 1")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with async_session_factory() as db:
        count_stmt = select(func.count()).select_from(ActionDedupe).where(
            ActionDedupe.created_at < cutoff
        )
        total_to_delete = (await db.execute(count_stmt)).scalar_one()
        print(f"cutoff={cutoff.isoformat()} eligible_rows={total_to_delete}")

        if dry_run or total_to_delete == 0:
            return

        deleted = 0
        while True:
            ids_stmt = (
                select(ActionDedupe.id)
                .where(ActionDedupe.created_at < cutoff)
                .order_by(ActionDedupe.id)
                .limit(batch_size)
            )
            ids = list((await db.execute(ids_stmt)).scalars().all())
            if not ids:
                break

            del_stmt = delete(ActionDedupe).where(ActionDedupe.id.in_(ids))
            await db.execute(del_stmt)
            await db.commit()

            deleted += len(ids)
            print(f"deleted_batch={len(ids)} deleted_total={deleted}")

    print(f"done deleted_total={deleted}")


async def main() -> None:
    args = parse_args()
    await cleanup(days=args.days, batch_size=args.batch_size, dry_run=args.dry_run)
    await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
