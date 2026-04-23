"""Premium quantile endpoint — exposes P10/P50/P90 for SFML-Stats UI. @zara"""

from __future__ import annotations

from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request

from .forecast_cache import get_or_refresh_forecast
from ..inference.engine import ForecastResult
from .schemas import (
    ForecastQuantilesResponse,
    GroupQuantiles,
    HourQuantiles,
)

router = APIRouter()


@router.get("/api/forecast/quantiles", response_model=ForecastQuantilesResponse)
async def quantile_forecast(
    request: Request,
    date: str | None = Query(default=None, description="Optional UTC date filter (YYYY-MM-DD)"),
) -> ForecastQuantilesResponse:
    """Return a fresh-enough forecast with all three quantiles. @zara"""
    state = request.app.state.tfs
    if state.engine is None or state.panel_groups is None:
        raise HTTPException(status_code=503, detail="No forecast available yet")

    result: ForecastResult = await get_or_refresh_forecast(state)
    tz = ZoneInfo(state.settings.timezone_str)

    filtered = result.hours
    if date:
        filtered = [h for h in result.hours if h.datetime_utc.astimezone(tz).date().isoformat() == date]

    hours: list[HourQuantiles] = []
    for hour in filtered:
        local_dt = hour.datetime_utc.astimezone(tz)
        hours.append(
            HourQuantiles(
                hour=local_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                p10=hour.p10_kwh,
                p50=hour.p50_kwh,
                p90=hour.p90_kwh,
                cloud_type=hour.cloud_type.value,
                groups=[
                    GroupQuantiles(
                        name=g.name,
                        p10=g.p10_kwh,
                        p50=g.p50_kwh,
                        p90=g.p90_kwh,
                        baseline_kwh=g.baseline_kwh,
                    )
                    for g in hour.groups
                ],
            )
        )

    return ForecastQuantilesResponse(
        generated_at=result.generated_at.astimezone(tz).strftime("%Y-%m-%dT%H:%M:%S"),
        total_kwh_p10=result.total_kwh_p10,
        total_kwh_p50=result.total_kwh_p50,
        total_kwh_p90=result.total_kwh_p90,
        validation_score=result.validation_score,
        horizon_hours=result.horizon_hours,
        lora_status=result.lora_status.value,
        hours=hours,
    )
