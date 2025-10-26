"""
Database module for SQLite connection and operations
"""
import aiosqlite
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

DATABASE_FILE = "database.db"

# SQL Schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT NOT NULL,
    website TEXT,
    industry TEXT NOT NULL,
    challenge TEXT,
    status TEXT DEFAULT 'pending',
    report_json TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_created ON submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email ON submissions(email);
"""


async def init_db():
    """Initialize the database with schema"""
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    print(f"[OK] Database initialized: {DATABASE_FILE}")


async def get_db() -> aiosqlite.Connection:
    """Get database connection"""
    db = await aiosqlite.connect(DATABASE_FILE)
    db.row_factory = aiosqlite.Row
    return db


# CRUD Operations

async def create_submission(
    name: str,
    email: str,
    company: str,
    website: Optional[str],
    industry: str,
    challenge: Optional[str],
) -> int:
    """Create a new submission"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO submissions (name, email, company, website, industry, challenge, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (name, email, company, website, industry, challenge),
        )
        await db.commit()
        return cursor.lastrowid


async def get_submission(submission_id: int) -> Optional[Dict[str, Any]]:
    """Get a submission by ID"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM submissions WHERE id = ?", (submission_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def get_all_submissions() -> List[Dict[str, Any]]:
    """Get all submissions ordered by created_at DESC"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM submissions ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_submission_status(
    submission_id: int,
    status: str,
    report_json: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """Update submission status and report"""
    async with await get_db() as db:
        await db.execute(
            """
            UPDATE submissions
            SET status = ?, report_json = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, report_json, error_message, submission_id),
        )
        await db.commit()


async def get_submissions_by_ip_today(ip_address: str) -> int:
    """
    Get count of submissions from an IP today.
    Note: This is a simplified version. In production, you'd store IP addresses.
    For MVP, we'll use in-memory rate limiting in the main app.
    """
    # This is a placeholder - actual implementation will be in-memory for MVP
    return 0


# Utility functions

async def count_submissions() -> int:
    """Count total submissions"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM submissions")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def count_submissions_by_status(status: str) -> int:
    """Count submissions by status"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM submissions WHERE status = ?", (status,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


if __name__ == "__main__":
    # Test database setup
    asyncio.run(init_db())
    print("Database setup complete!")
