# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""FastAPI application for Toorox ForeSight. @zara

Endpoints:
    GET  /health              — Health check
    GET  /forecast            — Current 72h forecast
    GET  /forecast/summary    — Daily summary (today/tomorrow/day3)
    GET  /model/status        — Model info, training status, parameters
    POST /forecast/trigger    — Manually trigger a new forecast
    GET  /metrics             — Prometheus metrics
    WS   /ws/forecast         — WebSocket live forecast updates
"""

from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class ForecastHour(BaseModel):
    """Single hour forecast data. @zara"""
    hour: datetime
    p10: float
    p50: float
    p90: float
    solar_elevation: float
    weather_condition: str = ""


class ForecastResponse(BaseModel):
    """72h forecast response. @zara"""
    generated_at: datetime
    forecast_type: str
    horizon_hours: int
    total_kwh_p50: float
    hours: list[ForecastHour]


class DailySummary(BaseModel):
    """Daily forecast summary. @zara"""
    date: str
    total_kwh_p10: float
    total_kwh_p50: float
    total_kwh_p90: float
    peak_hour: str
    peak_power_kw: float
    sunrise: str
    sunset: str


class ForecastSummaryResponse(BaseModel):
    """Multi-day summary. @zara"""
    generated_at: datetime
    days: list[DailySummary]


class ModelStatus(BaseModel):
    """Model information and status. @zara"""
    model_name: str = "ZaraTransformer"
    version: str
    total_parameters: int
    trainable_parameters: int
    device: str
    last_training: datetime | None
    last_forecast: datetime | None
    training_epochs: int
    best_val_loss: float | None
    onnx_available: bool


class TriggerResponse(BaseModel):
    """Forecast trigger response. @zara"""
    status: str
    forecast_id: str
    message: str


class ConnectionManager:
    """WebSocket connection manager for live updates. @zara"""

    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.remove(ws)

    async def broadcast(self, data: dict) -> None:
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                self.connections.remove(ws)


ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("foresight_api_starting")
    yield
    logger.info("foresight_api_shutting_down")


app = FastAPI(
    title="Toorox ForeSight",
    description="Local Transformer Solar Forecast Engine",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "engine": "zara-transformer"}


@app.get("/api/forecast", response_model=ForecastResponse)
async def get_forecast():
    from toorox_foresight.api.deps import get_forecast_service
    service = get_forecast_service()
    forecast = await service.get_current_forecast()
    if forecast is None:
        raise HTTPException(404, "No forecast available yet")
    return forecast


@app.get("/api/forecast/summary", response_model=ForecastSummaryResponse)
async def get_forecast_summary():
    from toorox_foresight.api.deps import get_forecast_service
    service = get_forecast_service()
    summary = await service.get_summary()
    if summary is None:
        raise HTTPException(404, "No forecast available yet")
    return summary


@app.get("/api/model/status", response_model=ModelStatus)
async def get_model_status():
    from toorox_foresight.api.deps import get_model_service
    service = get_model_service()
    return await service.get_status()


@app.post("/api/forecast/trigger", response_model=TriggerResponse)
async def trigger_forecast():
    from toorox_foresight.api.deps import get_forecast_service
    service = get_forecast_service()
    result = await service.trigger_forecast()
    return result


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    from prometheus_client import generate_latest
    return generate_latest().decode()


@app.websocket("/ws/forecast")
async def forecast_websocket(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
