"""pvlib-based astronomy utilities — solar position, clear-sky, daylight. @zara

Thin wrapper so the rest of the code does not import pvlib directly.
Caches results per (latitude, longitude, date) to avoid re-computation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd
import pvlib
from pvlib.location import Location


@dataclass(frozen=True)
class HourlyAstronomy:
    """Per-hour astronomy snapshot for one location. @zara"""

    sun_elevation_deg: float
    sun_azimuth_deg: float
    clear_sky_ghi_wm2: float
    clear_sky_dni_wm2: float
    clear_sky_dhi_wm2: float
    air_mass: float

    @property
    def is_daytime(self) -> bool:
        return self.sun_elevation_deg > 0.0


@dataclass(frozen=True)
class DailyAstronomy:
    """Sunrise, sunset, daylight hours, max elevation for one date. @zara"""

    date_iso: str
    sunrise_hour_float: float
    sunset_hour_float: float
    daylight_hours: float
    max_elevation_deg: float
    solar_noon_hour_float: float


@dataclass(frozen=True)
class SolarWindow:
    """Local-day solar window with UTC-normalized event times. @zara"""

    local_date_iso: str
    sunrise_utc: datetime
    sunset_utc: datetime
    window_start_utc: datetime
    window_end_utc: datetime


class AstronomyEngine:
    """Thin pvlib wrapper with per-day caching. @zara"""

    def __init__(self, latitude: float, longitude: float, altitude: float = 0.0) -> None:
        self._lat = latitude
        self._lon = longitude
        self._altitude = altitude
        self._loc = Location(latitude, longitude, tz="UTC", altitude=altitude)

    def _day_index(self, day_start_utc: datetime) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(
            [day_start_utc + timedelta(hours=h) for h in range(24)]
        )

    @lru_cache(maxsize=512)
    def daily(self, date_iso: str) -> DailyAstronomy:
        """Sunrise/sunset/daylight for a UTC date. @zara"""
        day_start = datetime.fromisoformat(date_iso).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        times = self._day_index(day_start)
        solpos = self._loc.get_solarposition(times)
        elevations = solpos["apparent_elevation"].to_numpy()

        day_hours = [h for h, e in enumerate(elevations) if e > 0]
        if not day_hours:
            return DailyAstronomy(
                date_iso=date_iso,
                sunrise_hour_float=6.0,
                sunset_hour_float=18.0,
                daylight_hours=0.0,
                max_elevation_deg=0.0,
                solar_noon_hour_float=12.0,
            )

        sunrise_h = float(day_hours[0])
        sunset_h = float(day_hours[-1] + 1)
        max_elev_idx = int(elevations.argmax())

        return DailyAstronomy(
            date_iso=date_iso,
            sunrise_hour_float=sunrise_h,
            sunset_hour_float=sunset_h,
            daylight_hours=max(0.0, sunset_h - sunrise_h),
            max_elevation_deg=float(elevations[max_elev_idx]),
            solar_noon_hour_float=float(max_elev_idx),
        )

    def solar_window_utc(
        self,
        local_date: date,
        timezone_name: str,
        before_sunrise_minutes: int = 60,
        after_sunset_minutes: int = 60,
    ) -> SolarWindow:
        """Precise local-day sunrise/sunset window normalized to UTC. @zara"""
        local_tz = ZoneInfo(timezone_name)
        local_midnight = datetime.combine(local_date, time.min, tzinfo=local_tz)
        local_loc = Location(
            self._lat,
            self._lon,
            tz=timezone_name,
            altitude=self._altitude,
        )
        # Force pvlib's SPA path so HA startup does not depend on optional
        # PyEphem being present in the add-on image.
        events = local_loc.get_sun_rise_set_transit(
            pd.DatetimeIndex([local_midnight]),
            method="spa",
        )
        sunrise_ts = events["sunrise"].iloc[0]
        sunset_ts = events["sunset"].iloc[0]

        if pd.isna(sunrise_ts) or pd.isna(sunset_ts):
            sunrise_local = local_midnight + timedelta(hours=6)
            sunset_local = local_midnight + timedelta(hours=18)
        else:
            sunrise_local = sunrise_ts.to_pydatetime(warn=False)
            sunset_local = sunset_ts.to_pydatetime(warn=False)
            if sunrise_local.tzinfo is None:
                sunrise_local = sunrise_local.replace(tzinfo=local_tz)
            if sunset_local.tzinfo is None:
                sunset_local = sunset_local.replace(tzinfo=local_tz)

        window_start_local = sunrise_local - timedelta(minutes=before_sunrise_minutes)
        window_end_local = sunset_local + timedelta(minutes=after_sunset_minutes)

        return SolarWindow(
            local_date_iso=local_date.isoformat(),
            sunrise_utc=sunrise_local.astimezone(timezone.utc),
            sunset_utc=sunset_local.astimezone(timezone.utc),
            window_start_utc=window_start_local.astimezone(timezone.utc),
            window_end_utc=window_end_local.astimezone(timezone.utc),
        )

    def hourly(self, when_utc: datetime) -> HourlyAstronomy:
        """Sun position + clear-sky for one UTC timestamp. @zara"""
        if when_utc.tzinfo is None:
            when_utc = when_utc.replace(tzinfo=timezone.utc)
        times = pd.DatetimeIndex([when_utc])
        solpos = self._loc.get_solarposition(times)
        clearsky = self._loc.get_clearsky(times, model="ineichen")

        elev = float(solpos["apparent_elevation"].iloc[0])
        azimuth = float(solpos["azimuth"].iloc[0])
        air_mass = self._air_mass_kasten_young(elev)

        return HourlyAstronomy(
            sun_elevation_deg=elev,
            sun_azimuth_deg=azimuth,
            clear_sky_ghi_wm2=float(clearsky["ghi"].iloc[0]),
            clear_sky_dni_wm2=float(clearsky["dni"].iloc[0]),
            clear_sky_dhi_wm2=float(clearsky["dhi"].iloc[0]),
            air_mass=air_mass,
        )

    def hourly_range(
        self,
        start_utc: datetime,
        hours: int,
    ) -> list[HourlyAstronomy]:
        """Sun position + clear-sky for a range of hours. @zara"""
        if start_utc.tzinfo is None:
            start_utc = start_utc.replace(tzinfo=timezone.utc)
        times = pd.DatetimeIndex(
            [start_utc + timedelta(hours=h) for h in range(hours)]
        )
        solpos = self._loc.get_solarposition(times)
        clearsky = self._loc.get_clearsky(times, model="ineichen")

        result: list[HourlyAstronomy] = []
        for i in range(hours):
            elev = float(solpos["apparent_elevation"].iloc[i])
            azimuth = float(solpos["azimuth"].iloc[i])
            result.append(
                HourlyAstronomy(
                    sun_elevation_deg=elev,
                    sun_azimuth_deg=azimuth,
                    clear_sky_ghi_wm2=float(clearsky["ghi"].iloc[i]),
                    clear_sky_dni_wm2=float(clearsky["dni"].iloc[i]),
                    clear_sky_dhi_wm2=float(clearsky["dhi"].iloc[i]),
                    air_mass=self._air_mass_kasten_young(elev),
                )
            )
        return result

    @staticmethod
    def _air_mass_kasten_young(elevation_deg: float) -> float:
        if elevation_deg <= 0.0:
            return 40.0
        zenith = 90.0 - elevation_deg
        cos_z = math.cos(math.radians(zenith))
        if cos_z <= 0.01:
            return 40.0
        denom = cos_z + 0.50572 * (96.07995 - zenith) ** -1.6364
        return min(40.0, 1.0 / denom)

    @staticmethod
    def erbs_decomposition(ghi: float, sun_elevation_deg: float) -> tuple[float, float]:
        """Simple Erbs decomposition GHI -> (DNI, DHI). @zara"""
        if sun_elevation_deg <= 0.0 or ghi <= 0.0:
            return 0.0, 0.0
        if sun_elevation_deg < 2.0:
            return 0.0, ghi
        zenith_rad = math.radians(90.0 - sun_elevation_deg)
        cos_z = max(math.cos(zenith_rad), 0.05)
        i0 = 1361.0
        kt = min(ghi / (i0 * cos_z), 1.2)
        if kt <= 0.22:
            df = 1.0 - 0.09 * kt
        elif kt <= 0.80:
            df = 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
        else:
            df = 0.165
        df = max(0.0, min(1.0, df))
        dhi = ghi * df
        dni_horiz = ghi - dhi
        dni = dni_horiz / cos_z if cos_z > 0.05 else 0.0
        return min(dni, 1400.0), max(0.0, dhi)
