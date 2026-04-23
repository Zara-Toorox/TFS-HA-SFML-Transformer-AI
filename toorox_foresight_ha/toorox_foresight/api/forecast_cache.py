"""Shared forecast cache/refresh logic for API routes. @zara"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException

from .state import AppState
from .runtime_context import refresh_panel_groups_from_sfml

if TYPE_CHECKING:
    from ..inference.engine import ForecastResult


async def get_or_refresh_forecast(state: AppState) -> "ForecastResult":
    """Return a fresh-enough forecast, refreshing via engine if TTL expired. @zara"""
    if state.engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")

    try:
        panel_groups = await refresh_panel_groups_from_sfml(state)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Panel-group refresh failed: {exc}") from exc

    ttl = timedelta(seconds=state.settings.timing.forecast_cache_ttl_seconds)
    if (
        state.last_result is not None
        and state.last_result_at is not None
        and datetime.now(timezone.utc) - state.last_result_at < ttl
    ):
        return state.last_result

    result = await state.engine.run_forecast(panel_groups)
    state.last_result = result
    state.last_result_at = result.generated_at
    return result
