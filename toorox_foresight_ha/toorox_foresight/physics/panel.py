"""Panel group data structures. @zara

Matches SFML's panel group semantics: a group is a set of panels sharing
the same orientation (tilt + azimuth) and a common kWp rating.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PanelGroup:
    """A single panel group — name, kWp, tilt, azimuth. @zara

    Azimuth convention: compass bearing (0=N, 90=E, 180=S, 270=W).
    Conversion to Open-Meteo convention happens at the weather boundary.
    """

    name: str
    power_kwp: float
    tilt_deg: float
    azimuth_deg: float

    def __post_init__(self) -> None:
        if self.power_kwp <= 0:
            raise ValueError(f"power_kwp must be > 0, got {self.power_kwp}")
        if not 0 <= self.tilt_deg <= 90:
            raise ValueError(f"tilt_deg must be in [0, 90], got {self.tilt_deg}")
        if not 0 <= self.azimuth_deg < 360:
            raise ValueError(f"azimuth_deg must be in [0, 360), got {self.azimuth_deg}")

    @property
    def tilt_rad(self) -> float:
        return math.radians(self.tilt_deg)

    @property
    def azimuth_rad(self) -> float:
        return math.radians(self.azimuth_deg)

    @property
    def azimuth_sin(self) -> float:
        return math.sin(self.azimuth_rad)

    @property
    def azimuth_cos(self) -> float:
        return math.cos(self.azimuth_rad)

    def to_geometry_features(self, max_kwp: float = 20.0) -> tuple[float, float, float]:
        """Normalized (tilt/90, azimuth_sin, azimuth_cos, kwp/max_kwp). @zara

        Returns 3-tuple for model input: tilt_normalized, azimuth_sin_normalized,
        azimuth_cos_normalized. kWp is given separately as a modulation scalar.
        """
        tilt_norm = self.tilt_deg / 90.0
        az_sin_norm = (self.azimuth_sin + 1.0) / 2.0
        az_cos_norm = (self.azimuth_cos + 1.0) / 2.0
        return tilt_norm, az_sin_norm, az_cos_norm

    def kwp_normalized(self, max_kwp: float = 20.0) -> float:
        return min(1.0, self.power_kwp / max_kwp)


@dataclass
class PanelGroupConfig:
    """System-level collection of panel groups. @zara"""

    groups: list[PanelGroup] = field(default_factory=list)

    def __post_init__(self) -> None:
        names = [g.name for g in self.groups]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate panel group names: {names}")

    @property
    def total_kwp(self) -> float:
        return sum(g.power_kwp for g in self.groups)

    @property
    def group_count(self) -> int:
        return len(self.groups)

    def get(self, name: str) -> PanelGroup | None:
        for g in self.groups:
            if g.name == name:
                return g
        return None

    @classmethod
    def from_dicts(cls, items: list[dict[str, Any]]) -> PanelGroupConfig:
        """Build from SFML-style dicts: {name, power_wp|capacity_kwp|kwp, azimuth, tilt}. @zara"""
        groups: list[PanelGroup] = []
        for idx, item in enumerate(items):
            name = str(item.get("name") or f"Gruppe {idx + 1}")
            power_kwp: float
            if "power_kwp" in item:
                power_kwp = float(item["power_kwp"])
            elif "capacity_kwp" in item:
                power_kwp = float(item["capacity_kwp"])
            elif "kwp" in item:
                power_kwp = float(item["kwp"])
            elif "power_wp" in item:
                power_kwp = float(item["power_wp"]) / 1000.0
            else:
                raise ValueError(f"Panel group {name} missing power specification")

            tilt = float(item.get("tilt_deg") or item.get("tilt") or 30.0)
            azimuth = float(item.get("azimuth_deg") or item.get("azimuth") or 180.0)
            groups.append(
                PanelGroup(
                    name=name,
                    power_kwp=power_kwp,
                    tilt_deg=tilt,
                    azimuth_deg=azimuth % 360.0,
                )
            )
        return cls(groups=groups)
