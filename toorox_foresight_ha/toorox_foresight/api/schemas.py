"""Pydantic models for API request/response bodies. @zara"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status payload. @zara"""

    status: str = "ok"
    version: str
    codename: str
    lora_status: str
    base_model_hash: str


class GroupKwhP50(BaseModel):
    """SFML-contract group entry: name + p50 only. @zara"""

    name: str
    p50: float


class HourForecastSFML(BaseModel):
    """SFML-consumer hour entry — single p50 + cloud_type + groups. @zara"""

    hour: str
    p50: float
    cloud_type: str
    groups: list[GroupKwhP50]


class ForecastResponseSFML(BaseModel):
    """SFML-contract response — p50 only per hour. @zara"""

    generated_at: str
    total_kwh_p50: float
    validation_score: float
    horizon_hours: int
    lora_status: str
    hours: list[HourForecastSFML]


class GroupQuantiles(BaseModel):
    """Full quantile triplet per group. @zara"""

    name: str
    p10: float
    p50: float
    p90: float
    baseline_kwh: float | None = None


class HourQuantiles(BaseModel):
    """Full quantile triplet per hour + per group. @zara"""

    hour: str
    p10: float
    p50: float
    p90: float
    cloud_type: str
    groups: list[GroupQuantiles]


class ForecastQuantilesResponse(BaseModel):
    """Premium endpoint — all three quantiles. @zara"""

    generated_at: str
    total_kwh_p10: float
    total_kwh_p50: float
    total_kwh_p90: float
    validation_score: float
    horizon_hours: int
    lora_status: str
    hours: list[HourQuantiles]


class AdminRefinetuneResponse(BaseModel):
    """Response of manual refinetune trigger. @zara"""

    accepted: bool
    reason: str
    triggered_at: str


class ErrorResponse(BaseModel):
    """Standard error payload. @zara"""

    detail: str
    context: dict | None = None
