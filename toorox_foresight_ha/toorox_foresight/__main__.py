# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""Toorox ForeSight entry point — starts API server. @zara

Uses serve_forecast script logic for the actual forecast engine,
exposed via FastAPI with proper async lifespan management.
"""

import os
import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
import torch
import uvicorn
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from toorox_foresight import __version__
from toorox_foresight.model.transformer import ZaraTransformer
from toorox_foresight.model.forecast_assembler import ForecastAssembler
from toorox_foresight.model.forecast_validator import ForecastValidator
from toorox_foresight.data.weather import WeatherClient
from toorox_foresight.data.weather_blender import WeatherBlender
from toorox_foresight.data.features import extract_features, BASE_FEATURE_COUNT
from toorox_foresight.physics.solar import SolarPhysics, PanelGroupConfig

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)
logger = structlog.get_logger()

DATA_DIR = Path(os.environ.get("FORESIGHT_DATA_DIR", "/data"))
SHARE_CHECKPOINT = Path("/share/foresight/checkpoints/best.safetensors")
DATA_CHECKPOINT = DATA_DIR / "checkpoints" / "best.safetensors"
CHECKPOINT = SHARE_CHECKPOINT if SHARE_CHECKPOINT.exists() else DATA_CHECKPOINT
DB_PATH = DATA_DIR / "foresight.db"
HORIZON = 24
SEQ_LEN = 72

LATITUDE = float(os.environ.get("FORESIGHT_LATITUDE", "52.65"))
LONGITUDE = float(os.environ.get("FORESIGHT_LONGITUDE", "13.49"))
ALTITUDE = float(os.environ.get("FORESIGHT_ALTITUDE", "0"))
TIMEZONE = os.environ.get("FORESIGHT_TIMEZONE", "Europe/Berlin")
PANEL_CAPACITY = float(os.environ.get("FORESIGHT_PANEL_CAPACITY", "5.0"))
PANEL_TILT = float(os.environ.get("FORESIGHT_PANEL_TILT", "30"))
PANEL_AZIMUTH = float(os.environ.get("FORESIGHT_PANEL_AZIMUTH", "180"))

_model = None
_last_forecast = None
_physics = None


def init_engine():
    global _physics
    _physics = SolarPhysics(
        latitude=LATITUDE, longitude=LONGITUDE, altitude=ALTITUDE,
        timezone=TIMEZONE,
        panel_groups=[
            PanelGroupConfig("Default", tilt=PANEL_TILT, azimuth=PANEL_AZIMUTH, capacity_kwp=PANEL_CAPACITY),
        ],
    )

    if CHECKPOINT.exists():
        from safetensors.torch import load_file
        global _model
        _model = ZaraTransformer(
            n_temporal_features=BASE_FEATURE_COUNT,
            n_weather_features=12, n_physics_features=8,
            d_model=256, n_heads=8,
            n_encoder_layers=6, n_decoder_layers=4,
            d_ff=1024, forecast_horizon=HORIZON,
            patch_size=6, n_quantiles=3, n_panel_groups=1,
            n_experts=4, top_k_experts=2,
            dropout=0.0, use_rope=True, use_flash=True,
            gradient_checkpointing=False,
        )
        try:
            state = load_file(str(CHECKPOINT), device="cpu")
            _model.load_state_dict(state)
            _model.eval()
            logger.info("model_loaded", params=_model.count_parameters()["total"])
        except Exception as e:
            logger.warning("model_load_failed", error=str(e))
            _model = None
    else:
        logger.warning("no_checkpoint_found", path=str(CHECKPOINT))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("foresight_starting", version=__version__,
                latitude=LATITUDE, longitude=LONGITUDE, capacity=PANEL_CAPACITY)
    init_engine()
    yield
    logger.info("foresight_shutting_down")


app = FastAPI(title="Toorox ForeSight", version=__version__, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "engine": "zara-transformer",
        "version": __version__,
        "model_loaded": _model is not None,
    }


@app.get("/api/forecast")
async def get_forecast():
    if _last_forecast is None:
        return {"status": "no_forecast_yet", "message": "Generate first forecast via POST /api/forecast/trigger"}
    return _last_forecast


@app.post("/api/forecast/trigger")
async def trigger():
    if _model is None:
        return {"status": "error", "message": "No model loaded — train first"}
    return {"status": "ok", "message": "Forecast generation pending — feature in development"}


@app.get("/api/model/status")
async def model_status():
    return {
        "model_name": "ZaraTransformer",
        "version": __version__,
        "total_parameters": _model.count_parameters()["total"] if _model else 0,
        "model_loaded": _model is not None,
        "device": "cpu",
        "checkpoint_exists": CHECKPOINT.exists(),
    }


STATIC_DIR = Path("/app/toorox_foresight/static")
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def main():
    logger.info("uvicorn_start", host="0.0.0.0", port=8780)
    uvicorn.run(app, host="0.0.0.0", port=8780, log_level="info")


if __name__ == "__main__":
    main()
