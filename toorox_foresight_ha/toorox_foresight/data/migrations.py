"""Schema migrations for the TFS local state database. @zara

Applied in order by version number. Each migration is idempotent via
CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Migration:
    """A single schema migration step. @zara"""

    version: int
    description: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        description="Initial schema — forecasts, weights, baseline cache, training history",
        statements=(
            """CREATE TABLE IF NOT EXISTS tfs_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS tfs_forecast_run (
                forecast_id TEXT PRIMARY KEY,
                generated_at TEXT NOT NULL,
                base_model_hash TEXT NOT NULL,
                lora_hash TEXT,
                horizon_hours INTEGER NOT NULL,
                total_kwh_p10 REAL NOT NULL,
                total_kwh_p50 REAL NOT NULL,
                total_kwh_p90 REAL NOT NULL,
                validation_score REAL NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS tfs_forecast_hourly (
                forecast_id TEXT NOT NULL,
                target_datetime TEXT NOT NULL,
                group_name TEXT NOT NULL,
                p10 REAL NOT NULL,
                p50 REAL NOT NULL,
                p90 REAL NOT NULL,
                cloud_type TEXT,
                baseline_kwh REAL NOT NULL,
                gain_p50 REAL NOT NULL,
                PRIMARY KEY (forecast_id, target_datetime, group_name),
                FOREIGN KEY (forecast_id)
                    REFERENCES tfs_forecast_run(forecast_id) ON DELETE CASCADE
            )""",
            """CREATE INDEX IF NOT EXISTS idx_tfs_forecast_hourly_target
                ON tfs_forecast_hourly(target_datetime)""",
            """CREATE TABLE IF NOT EXISTS tfs_weather_blender_weights (
                source TEXT NOT NULL,
                cloud_type TEXT NOT NULL,
                variable TEXT NOT NULL,
                weight REAL NOT NULL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL,
                PRIMARY KEY (source, cloud_type, variable)
            )""",
            """CREATE TABLE IF NOT EXISTS tfs_baseline_cache (
                target_date TEXT NOT NULL,
                hour INTEGER NOT NULL CHECK(hour BETWEEN 0 AND 23),
                group_name TEXT NOT NULL,
                baseline_kwh REAL NOT NULL,
                poa_wm2 REAL NOT NULL,
                computed_at TEXT NOT NULL,
                PRIMARY KEY (target_date, hour, group_name)
            )""",
            """CREATE TABLE IF NOT EXISTS tfs_training_history (
                run_id TEXT PRIMARY KEY,
                run_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                samples INTEGER,
                epochs INTEGER,
                best_val_loss REAL,
                base_model_hash TEXT,
                lora_hash TEXT,
                notes TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS tfs_performance (
                date TEXT PRIMARY KEY,
                mae_p50 REAL,
                rmse_p50 REAL,
                coverage_p10 REAL,
                coverage_p90 REAL,
                sample_count INTEGER
            )""",
            """CREATE TABLE IF NOT EXISTS tfs_weather_cache (
                source TEXT NOT NULL,
                forecast_date TEXT NOT NULL,
                hour INTEGER NOT NULL,
                variable TEXT NOT NULL,
                value REAL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (source, forecast_date, hour, variable)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_tfs_weather_cache_date_hour
                ON tfs_weather_cache(forecast_date, hour)""",
        ),
    ),
)


def current_schema_version() -> int:
    """Highest known migration version. @zara"""
    return max(m.version for m in MIGRATIONS)
