# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""Database engine and session management. @zara"""

from pathlib import Path
import sqlite3
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
import structlog

from toorox_foresight.data.models import Base

logger = structlog.get_logger()


HOURLY_RECORDS_EXTRA_COLUMNS = {
    "battery_charge_kwh": "REAL",
    "battery_discharge_kwh": "REAL",
    "grid_export_kwh": "REAL",
    "grid_import_kwh": "REAL",
    "self_consumption_kwh": "REAL",
}


def _migrate_schema(db_path: str) -> None:
    """Add columns introduced in later versions to existing hourly_records. @zara"""
    if not Path(db_path).exists():
        return
    conn = sqlite3.connect(db_path)
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(hourly_records)")}
        if not existing:
            return
        added = []
        for col, col_type in HOURLY_RECORDS_EXTRA_COLUMNS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE hourly_records ADD COLUMN {col} {col_type}")
                added.append(col)
        if added:
            conn.commit()
            logger.info("schema_migrated", table="hourly_records", added=added)
    finally:
        conn.close()


class Database:
    """Async SQLAlchemy database manager. @zara"""

    def __init__(self, db_url: str = "sqlite+aiosqlite:///data/foresight.db") -> None:
        self.db_url = db_url
        self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init(self) -> None:
        db_path = self.db_url.replace("sqlite+aiosqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        _migrate_schema(db_path)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("database_initialized", url=self.db_url)

    async def get_session(self) -> AsyncSession:
        return self.session_factory()

    async def close(self) -> None:
        await self.engine.dispose()
