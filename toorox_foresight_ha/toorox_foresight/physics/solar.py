# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""pvlib-based solar physics engine for Toorox ForeSight. @zara

Provides:
- Clear-sky GHI/DNI/DHI for any location and time
- POA irradiance for tilted panels (per group)
- Theoretical max kWh per hour per panel group
- Sun position (elevation, azimuth)
- Air mass, day length, sunrise/sunset
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import numpy as np
import pvlib
from pvlib.location import Location
from pvlib.irradiance import get_total_irradiance
import structlog

logger = structlog.get_logger()


@dataclass
class PanelGroupConfig:
    """Single panel group physical parameters. @zara"""
    name: str
    tilt: float
    azimuth: float
    capacity_kwp: float
    efficiency: float = 0.18
    temp_coeff: float = -0.004


@dataclass
class SolarHour:
    """Physics data for a single hour. @zara"""
    timestamp: datetime
    sun_elevation: float = 0.0
    sun_azimuth: float = 0.0
    clear_sky_ghi: float = 0.0
    clear_sky_dni: float = 0.0
    clear_sky_dhi: float = 0.0
    air_mass: float = 40.0
    daylight_hours: float = 0.0
    hours_after_sunrise: float = 0.0
    hours_before_sunset: float = 0.0
    hours_since_solar_noon: float = 0.0
    day_progress: float = 0.0
    is_daytime: bool = False
    group_poa: dict[str, float] = field(default_factory=dict)
    group_max_kwh: dict[str, float] = field(default_factory=dict)
    total_max_kwh: float = 0.0


class SolarPhysics:
    """pvlib-based solar physics calculator. @zara"""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        altitude: float = 0.0,
        timezone: str = "Europe/Berlin",
        panel_groups: list[PanelGroupConfig] | None = None,
    ) -> None:
        self.location = Location(latitude, longitude, timezone, altitude)
        self.tz = ZoneInfo(timezone)
        self.panel_groups = panel_groups or []
        self.total_capacity = sum(g.capacity_kwp for g in self.panel_groups)
        logger.info(
            "physics_init",
            lat=latitude, lon=longitude,
            groups=len(self.panel_groups),
            capacity_kwp=self.total_capacity,
        )

    def calculate_hours(
        self,
        start: datetime,
        n_hours: int = 72,
    ) -> list[SolarHour]:
        """Calculate physics data for n_hours starting from start. @zara"""
        import pandas as pd
        base = start.replace(tzinfo=self.tz) if start.tzinfo is None else start
        times_pd = pd.DatetimeIndex([base + timedelta(hours=i) for i in range(n_hours)])

        solpos = self.location.get_solarposition(times_pd)
        clearsky = self.location.get_clearsky(times_pd, model="ineichen")

        sunrise_sunset = self._get_sunrise_sunset(start)

        hours = []
        for i in range(n_hours):
            ts = start + timedelta(hours=i)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=self.tz)

            elev = float(solpos["apparent_elevation"].iloc[i])
            azi = float(solpos["azimuth"].iloc[i])
            ghi = float(clearsky["ghi"].iloc[i])
            dni = float(clearsky["dni"].iloc[i])
            dhi = float(clearsky["dhi"].iloc[i])

            am = float(solpos["apparent_elevation"].iloc[i])
            if am > 0:
                am = float(pvlib.atmosphere.get_relative_airmass(90 - am))
            else:
                am = 40.0

            is_day = elev > 0
            sr = sunrise_sunset.get(ts.date(), {})
            sunrise_h = sr.get("sunrise", 6.0)
            sunset_h = sr.get("sunset", 18.0)
            noon_h = (sunrise_h + sunset_h) / 2
            daylight = max(0, sunset_h - sunrise_h)
            current_h = ts.hour + ts.minute / 60

            group_poa = {}
            group_max = {}
            total_max = 0.0

            if is_day and ghi > 0:
                for g in self.panel_groups:
                    poa = self._calculate_poa(elev, azi, dni, dhi, ghi, g.tilt, g.azimuth)
                    group_poa[g.name] = poa
                    max_kwh = poa / 1000.0 * g.capacity_kwp * g.efficiency / 0.18
                    group_max[g.name] = round(max_kwh, 4)
                    total_max += max_kwh

            hours.append(SolarHour(
                timestamp=ts,
                sun_elevation=round(elev, 2),
                sun_azimuth=round(azi, 2),
                clear_sky_ghi=round(ghi, 1),
                clear_sky_dni=round(dni, 1),
                clear_sky_dhi=round(dhi, 1),
                air_mass=round(am, 2),
                daylight_hours=round(daylight, 2),
                hours_after_sunrise=round(max(0, current_h - sunrise_h), 2) if is_day else 0,
                hours_before_sunset=round(max(0, sunset_h - current_h), 2) if is_day else 0,
                hours_since_solar_noon=round(current_h - noon_h, 2),
                day_progress=round(max(0, min(1, (current_h - sunrise_h) / max(daylight, 0.1))), 3) if is_day else 0,
                is_daytime=is_day,
                group_poa=group_poa,
                group_max_kwh=group_max,
                total_max_kwh=round(total_max, 4),
            ))

        daily_total = sum(h.total_max_kwh for h in hours if h.is_daytime)
        logger.info(
            "physics_calculated",
            hours=n_hours,
            daytime_hours=sum(1 for h in hours if h.is_daytime),
            clearsky_total_kwh=round(daily_total, 2),
        )

        return hours

    def _calculate_poa(
        self,
        sun_elev: float,
        sun_azi: float,
        dni: float,
        dhi: float,
        ghi: float,
        tilt: float,
        surface_azimuth: float,
    ) -> float:
        """Calculate plane-of-array irradiance for a tilted surface. @zara"""
        try:
            result = get_total_irradiance(
                surface_tilt=tilt,
                surface_azimuth=surface_azimuth,
                solar_zenith=90 - sun_elev,
                solar_azimuth=sun_azi,
                dni=dni,
                ghi=ghi,
                dhi=dhi,
                model="isotropic",
            )
            poa = float(result["poa_global"])
            return max(0.0, poa)
        except Exception:
            return max(0.0, ghi)

    def _get_sunrise_sunset(self, start: datetime) -> dict:
        """Get sunrise/sunset for each day in the forecast period. @zara"""
        result = {}
        for day_offset in range(4):
            date = (start + timedelta(days=day_offset)).date()
            try:
                import pandas as pd
                sun_times = self.location.get_sun_rise_set_transit(
                    pd.DatetimeIndex([datetime(date.year, date.month, date.day, 12, tzinfo=self.tz)])
                )
                sunrise = pd.Timestamp(sun_times["sunrise"].iloc[0])
                sunset = pd.Timestamp(sun_times["sunset"].iloc[0])
                result[date] = {
                    "sunrise": sunrise.hour + sunrise.minute / 60,
                    "sunset": sunset.hour + sunset.minute / 60,
                }
            except Exception:
                result[date] = {"sunrise": 6.0, "sunset": 18.0}
        return result
