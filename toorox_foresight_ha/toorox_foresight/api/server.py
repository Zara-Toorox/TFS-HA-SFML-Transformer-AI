"""FastAPI application factory + lifespan wiring. @zara"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
import orjson
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .. import __codename__, __version__
from ..astronomy import AstronomyEngine
from ..config import TFSSettings, get_settings
from ..data.sfml_reader import SFMLReader
from ..data.state_db import StateDB
from ..inference.engine import ForecastEngine
from ..inference.lora_loader import AdapterStatus
from ..inference.lora_loader import LoRALoader
from ..logging_setup import configure_logging, get_logger
from ..physics.panel import PanelGroupConfig
from ..security.model_crypto import resolve_base_checkpoint
from ..training.runner import create_finetune_runner
from ..weather.blender import WeatherBlender
from .routes_admin import router as admin_router
from .routes_forecast import router as forecast_router
from .routes_quantiles import router as quantiles_router
from .scheduler import ForecastScheduler
from .state import AppState

logger = get_logger(__name__)


class RuntimeBootstrapError(RuntimeError):
    """Raised when TFS cannot establish a trustworthy runtime context. @zara"""

async def _resolve_runtime_context(
    settings: TFSSettings,
    sfml: SFMLReader,
) -> tuple[float, float, PanelGroupConfig, dict[str, str]]:
    """Resolve location + panel groups from trusted runtime sources. @zara"""
    lat = settings.latitude
    lon = settings.longitude
    location_source = "settings"
    panel_group_source = "sfml"

    try:
        system_info = await sfml.get_system_info()
    except Exception as exc:
        raise RuntimeBootstrapError(f"SFML system info bootstrap failed: {exc}") from exc

    if system_info is not None:
        if lat is None:
            lat = system_info.latitude
            location_source = "sfml"
        if lon is None:
            lon = system_info.longitude
            location_source = "sfml"

    if lat is None or lon is None:
        raise RuntimeBootstrapError(
            "TFS startup aborted: no trusted latitude/longitude available from config or SFML"
        )

    try:
        sfml_groups = await sfml.get_panel_groups()
    except Exception as exc:
        raise RuntimeBootstrapError(f"SFML panel-group bootstrap failed: {exc}") from exc

    if not sfml_groups:
        raise RuntimeBootstrapError(
            "TFS startup aborted: no trusted panel groups available from SFML"
        )

    panel_groups = PanelGroupConfig.from_dicts(
        [
            {
                "name": g.name,
                "power_kwp": g.power_kwp,
                "tilt": g.tilt_deg,
                "azimuth": g.azimuth_deg,
            }
            for g in sfml_groups
        ]
    )
    return lat, lon, panel_groups, {
        "location_source": location_source,
        "panel_group_source": panel_group_source,
    }


async def _bootstrap(app: FastAPI) -> AppState:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "tfs_bootstrap",
        version=__version__,
        codename=__codename__,
        state_dir=str(settings.state_dir),
    )

    supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
    if supervisor_token:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "http://supervisor/info",
                    headers={"Authorization": f"Bearer {supervisor_token}"},
                    timeout=5.0,
                )
                tz_str = resp.json().get("data", {}).get("timezone")
                if tz_str:
                    settings.timezone_str = tz_str
                    logger.info("timezone_from_supervisor", timezone=tz_str)
        except Exception as exc:
            logger.warning("timezone_supervisor_failed", error=str(exc))

    state = AppState(settings=settings)

    state.state_db = StateDB(settings.state_db_path)
    await state.state_db.connect()

    sfml = SFMLReader(settings.sfml.db_path, timeout_seconds=settings.sfml.query_timeout_seconds)
    state.sfml_reader = sfml

    lat, lon, panel_groups, runtime_sources = await _resolve_runtime_context(settings, sfml)
    logger.info(
        "runtime_context_resolved",
        latitude=lat,
        longitude=lon,
        location_source=runtime_sources["location_source"],
        panel_groups=panel_groups.group_count,
        panel_group_source=runtime_sources["panel_group_source"],
    )

    state.astronomy = AstronomyEngine(lat, lon)

    state.blender = WeatherBlender(
        latitude=lat,
        longitude=lon,
        state_db=state.state_db,
        astronomy=state.astronomy,
        open_meteo_url=settings.weather.open_meteo_url,
        open_meteo_models=tuple(settings.weather.open_meteo_models),
        brightsky_url=settings.weather.brightsky_url,
        timeout_seconds=settings.weather.request_timeout_seconds,
    )
    await state.blender.initialize()

    base_ckpt = resolve_base_checkpoint(settings.base_model_dir)
    state.lora_loader = LoRALoader(
        base_checkpoint=base_ckpt,
        lora_dir=settings.lora_dir,
        lora_rank=settings.training.lora_rank,
        lora_alpha=settings.training.lora_alpha,
        lora_dropout=settings.training.lora_dropout,
    )

    state.engine = ForecastEngine(
        architecture=settings.model,
        physics_cfg=settings.physics,
        base_checkpoint_path=base_ckpt,
        blender=state.blender,
        astronomy=state.astronomy,
        sfml_reader=sfml,
        state_db=state.state_db,
        lora_loader=state.lora_loader,
        device=None,
    )
    state.panel_groups = panel_groups

    state.engine.load_model(instance_id="default")
    adapter_info = state.lora_loader.inspect("default")
    logger.info(
        "startup_notification",
        version=__version__,
        codename=__codename__,
        panel_groups=panel_groups.group_count,
        base_model_path=str(base_ckpt),
        base_model_hash=state.lora_loader.base_hash,
        adapter_status=adapter_info.status.value,
        adapter_path=str(adapter_info.path),
    )

    state.extras["finetune_runner"] = await create_finetune_runner(
        settings=settings,
        sfml_reader=sfml,
        astronomy=state.astronomy,
        lora_loader=state.lora_loader,
        base_checkpoint=base_ckpt,
        state_db=state.state_db,
        engine=state.engine,
    )

    state.scheduler = ForecastScheduler(state)
    state.scheduler.start()
    accepted, reason = state.scheduler.schedule_startup_finetune_if_needed()
    if accepted:
        logger.info("startup_notification_refinetune", status="queued", reason=reason)
    elif adapter_info.status in (AdapterStatus.INVALIDATED, AdapterStatus.MISSING):
        logger.info(
            "startup_notification_refinetune",
            status="not_queued",
            reason=reason,
            adapter_status=adapter_info.status.value,
        )

    app.state.tfs = state
    return state


async def _shutdown(state: AppState) -> None:
    if state.scheduler is not None:
        state.scheduler.stop()
    if state.state_db is not None:
        await state.state_db.close()
    logger.info("tfs_shutdown_complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = await _bootstrap(app)
    try:
        yield
    finally:
        await _shutdown(state)


def create_app() -> FastAPI:
    """Factory for the FastAPI app. @zara"""
    app = FastAPI(
        title="Toorox ForeSight HA",
        description="Transformer-based solar forecast ensemble member",
        version=__version__,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    app.include_router(forecast_router)
    app.include_router(quantiles_router)
    app.include_router(admin_router)
    return app


app = create_app()
