# backend/check_inventory.py
import asyncio
import sqlalchemy as sa
from app.core.database import AsyncSessionLocal
from app.models.puzzle import Puzzle

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            sa.select(Puzzle.assigned_date, Puzzle.puzzle_type).order_by(
                Puzzle.assigned_date.nulls_last(), 
                Puzzle.assigned_date
            )
        )
        rows = result.all()
        assigned = [r for r in rows if r[0] is not None]
        unassigned = [r for r in rows if r[0] is None]
        
        print(f"\n--- SCHEDULED HORIZON ({len(assigned)} Days) ---")
        for date, ptype in assigned:
            print(f"{date}: {ptype}")
            
        print(f"\n--- UNASSIGNED RESERVE POOL ({len(unassigned)} Puzzles) ---")
        for _, ptype in unassigned:
            print(f"Reserve: {ptype}")

if __name__ == "__main__":
    asyncio.run(check())