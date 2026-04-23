"""SFML-contract forecast routes. @zara

Implements the endpoints SFML expects:
  GET  /health
  POST /api/forecast/run?forecast_type=sfml
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request

from .. import __codename__, __version__
from ..inference.engine import ForecastResult
from .forecast_cache import get_or_refresh_forecast
from .schemas import (
    ForecastResponseSFML,
    GroupKwhP50,
    HealthResponse,
    HourForecastSFML,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Return service health for SFML availability check. @zara"""
    state = request.app.state.tfs
    lora_status = "unknown"
    base_hash = "no-base"
    if state.engine is not None:
        lora_status = state.engine._lora_status.value if state.engine._lora_status else "unknown"
    if state.lora_loader is not None:
        base_hash = state.lora_loader.base_hash
    return HealthResponse(
        status="ok",
        version=__version__,
        codename=__codename__,
        lora_status=lora_status,
        base_model_hash=base_hash,
    )


@router.post("/api/forecast/run", response_model=ForecastResponseSFML)
async def run_forecast(
    request: Request,
    forecast_type: str = Query(default="sfml"),
) -> ForecastResponseSFML:
    """Run a fresh forecast OR return the cached one if fresh enough. @zara"""
    state = request.app.state.tfs
    if state.engine is None or state.panel_groups is None:
        raise HTTPException(status_code=503, detail="Engine not ready")

    result = await get_or_refresh_forecast(state)
    tz = ZoneInfo(state.settings.timezone_str)
    return _to_sfml_response(result, tz)


def _to_sfml_response(result: ForecastResult, tz: ZoneInfo) -> ForecastResponseSFML:
    hours: list[HourForecastSFML] = []
    for hour in result.hours:
        local_dt = hour.datetime_utc.astimezone(tz)
        hours.append(
            HourForecastSFML(
                hour=local_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                p50=hour.p50_kwh,
                cloud_type=hour.cloud_type.value,
                groups=[GroupKwhP50(name=g.name, p50=g.p50_kwh) for g in hour.groups],
            )
        )
    return ForecastResponseSFML(
        generated_at=result.generated_at.astimezone(tz).strftime("%Y-%m-%dT%H:%M:%S"),
        total_kwh_p50=result.total_kwh_p50,
        validation_score=result.validation_score,
        horizon_hours=result.horizon_hours,
        lora_status=result.lora_status.value,
        hours=hours,
    )
