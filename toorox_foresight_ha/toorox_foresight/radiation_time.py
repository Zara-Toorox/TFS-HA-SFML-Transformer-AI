"""Move provider radiation from the hour-ending label onto [h, h+1). @zara

Open-Meteo (every model, including ICON-D2 via icon_seamless, GFS, IFS):
shortwave_radiation, direct_radiation, diffuse_radiation, direct_normal_irradiance,
global_tilted_irradiance and terrestrial_radiation are the mean of the hour
that ends at the timestamp. temperature_2m, relative_humidity_2m,
surface_pressure, cloud_cover*, wind_speed_10m, visibility, snow_depth and
weather_code are instantaneous at the timestamp.
precipitation, rain and snowfall are preceding-hour sums and stay put: this
contract is radiation only.

Bright Sky ``solar`` is the irradiation of the previous 60 minutes, stored on
that timestamp. temperature, cloud_cover, wind_speed, pressure, humidity and
visibility are the observation at the timestamp.

TFS hour h is [h, h+1), matching SFML. The shift runs once. A row already
marked interval_start is returned unchanged. A missing successor becomes None.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

RADIATION_HOUR_BASIS_INTERVAL_START = "interval_start"
RADIATION_HOUR_BASIS_META_KEY = "radiation_hour_basis"

# Canonical names plus the provider names that may still be on a row.
PROVIDER_RADIATION_FIELDS = (
    "ghi",
    "dni",
    "dhi",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",
    "global_tilted_irradiance",
    "terrestrial_radiation",
)

# Blender weights learned while source GHI was still the hour-ending cache join.
STALE_RADIATION_WEIGHT_VARIABLES = PROVIDER_RADIATION_FIELDS


def hour_start_utc(when: datetime) -> datetime:
    """Floor a timestamp to the UTC hour. Naive values are treated as UTC. @zara"""
    when = when.replace(tzinfo=UTC) if when.tzinfo is None else when.astimezone(UTC)
    return when.replace(minute=0, second=0, microsecond=0)


def align_provider_radiation_to_interval_start(entries: list[dict]) -> list[dict]:
    """Copy radiation from timestamp t+1h onto the row labelled t.

    Non-radiation fields stay on t. The row at the last timestamp has no
    successor, so its radiation fields become None. Marked rows are not moved
    again.
    """
    by_hour: dict[datetime, dict] = {}
    for entry in entries:
        stamp = entry.get("datetime")
        if stamp is None:
            continue
        by_hour[hour_start_utc(stamp)] = entry

    aligned: list[dict] = []
    for entry in entries:
        row = dict(entry)
        stamp = row.get("datetime")
        if stamp is None or row.get("radiation_hour_basis") == RADIATION_HOUR_BASIS_INTERVAL_START:
            aligned.append(row)
            continue
        label = hour_start_utc(stamp)
        successor = by_hour.get(label + timedelta(hours=1))
        for field in PROVIDER_RADIATION_FIELDS:
            if field not in row and (successor is None or field not in successor):
                continue
            row[field] = successor.get(field) if successor is not None else None
        row["datetime"] = label
        row["radiation_hour_basis"] = RADIATION_HOUR_BASIS_INTERVAL_START
        aligned.append(row)
    return aligned


def select_interval_window(entries: list[dict], start_utc: datetime, hours: int) -> list[dict]:
    """Keep labels in [start, start+hours). Hours outside that window are dropped. @zara"""
    start = hour_start_utc(start_utc)
    end = start + timedelta(hours=hours)
    chosen = [
        entry
        for entry in entries
        if entry.get("datetime") is not None and start <= hour_start_utc(entry["datetime"]) < end
    ]
    chosen.sort(key=lambda entry: hour_start_utc(entry["datetime"]))
    return chosen


def finalize_provider_hours(entries: list[dict], start_utc: datetime, hours: int) -> list[dict]:
    """Align radiation once, then drop the successor hour used only as a donor. @zara"""
    return select_interval_window(
        align_provider_radiation_to_interval_start(entries),
        start_utc,
        hours,
    )
