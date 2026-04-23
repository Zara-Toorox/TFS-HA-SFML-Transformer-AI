"""Async scheduler — 2x-daily forecasts + nightly LoRA finetune.

Uses APScheduler with an AsyncIO executor. Configurable via TFSSettings.timing. @zara
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from types import SimpleNamespace

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

from ..astronomy import AstronomyEngine
from ..inference.lora_loader import AdapterStatus
from ..logging_setup import get_logger
from .runtime_context import refresh_panel_groups_from_sfml
from .state import AppState

logger = get_logger(__name__)


class ForecastScheduler:
    """Time-based forecast + finetune trigger. @zara"""

    def __init__(self, state: AppState) -> None:
        self._state = state
        self._timezone = ZoneInfo(state.settings.timezone_str)
        self._scheduler = AsyncIOScheduler(timezone=self._timezone)
        self._finetune_in_progress = False
        self._forecast_in_progress = False

    def start(self) -> None:
        """Register jobs and start the scheduler. @zara"""
        settings = self._state.settings
        for spec in settings.timing.forecast_times:
            if _is_solar_spec(spec):
                self._schedule_next_solar_forecast(spec)
            else:
                trigger = self._build_fixed_trigger(spec)
                self._scheduler.add_job(
                    self._run_forecast,
                    trigger=trigger,
                    name=f"forecast_{spec}",
                    misfire_grace_time=300,
                )
                logger.info("forecast_job_registered", spec=spec, kind="fixed")

        if settings.timing.auto_finetune:
            hh, mm = _parse_hhmm(settings.timing.finetune_time)
            self._scheduler.add_job(
                self._run_finetune,
                trigger=CronTrigger(hour=hh, minute=mm, timezone=self._timezone),
                name="nightly_finetune",
                misfire_grace_time=3600,
            )
            logger.info(
                "finetune_job_registered",
                at=settings.timing.finetune_time,
                timezone=self._state.settings.timezone_str,
            )

        self._scheduler.start()
        logger.info("scheduler_started", timezone=self._state.settings.timezone_str)

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    def schedule_immediate_finetune(self, force: bool = False) -> tuple[bool, str]:
        """Queue a finetune to run ASAP. @zara"""
        if self._finetune_in_progress:
            return False, "finetune already running"
        asyncio.create_task(self._run_finetune(force=force))
        return True, "queued"

    def schedule_startup_finetune_if_needed(self) -> tuple[bool, str]:
        """Queue finetune on startup if the active adapter is not valid. @zara"""
        if not self._state.settings.timing.auto_finetune:
            return False, "auto finetune disabled"
        if self._state.lora_loader is None:
            return False, "lora loader missing"

        info = self._state.lora_loader.inspect("default")
        if info.status not in (AdapterStatus.INVALIDATED, AdapterStatus.MISSING):
            return False, f"adapter status {info.status.value}"

        accepted, reason = self.schedule_immediate_finetune(force=False)
        if accepted:
            requested_at = datetime.now(timezone.utc)
            self._state.last_refinetune_requested_at = requested_at
            self._state.refinetune_status = "queued"
            self._state.extras["startup_refinetune"] = SimpleNamespace(
                requested_at=requested_at,
                adapter_status=info.status.value,
                base_hash_current=info.base_hash_current,
                base_hash_adapter=info.base_hash_adapter,
            )
            logger.info(
                "startup_refinetune_queued",
                adapter_status=info.status.value,
                base_hash_current=info.base_hash_current,
                base_hash_adapter=info.base_hash_adapter,
                requested_at=requested_at.isoformat(),
            )
        return accepted, reason

    def _build_fixed_trigger(self, spec: str):
        spec = spec.strip()
        hh, mm = _parse_hhmm(spec)
        return CronTrigger(hour=hh, minute=mm, timezone=self._timezone)

    def _astronomy(self) -> AstronomyEngine:
        if self._state.astronomy is not None:
            return self._state.astronomy
        settings = self._state.settings
        return AstronomyEngine(settings.latitude, settings.longitude)

    def _schedule_next_solar_forecast(
        self,
        spec: str,
        reference_utc: datetime | None = None,
    ) -> None:
        next_run_utc = self._resolve_next_solar_run(spec, reference_utc)
        job_id = _solar_job_id(spec)
        self._scheduler.add_job(
            self._run_solar_forecast,
            trigger=DateTrigger(run_date=next_run_utc),
            kwargs={"spec": spec},
            id=job_id,
            name=f"forecast_{spec}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info(
            "forecast_job_registered",
            spec=spec,
            kind="solar_dynamic",
            next_run_utc=next_run_utc.isoformat(),
            next_run_local=next_run_utc.astimezone(self._timezone).isoformat(),
        )

    def _resolve_next_solar_run(
        self,
        spec: str,
        reference_utc: datetime | None = None,
    ) -> datetime:
        event_name, offset_minutes = _parse_solar_spec(spec)
        reference_utc = reference_utc or datetime.now(timezone.utc)
        astro = self._astronomy()

        for day_offset in range(0, 4):
            local_date = (
                reference_utc.astimezone(self._timezone).date()
                + timedelta(days=day_offset)
            )
            solar_window = astro.solar_window_utc(
                local_date,
                timezone_name=self._state.settings.timezone_str,
                before_sunrise_minutes=60,
                after_sunset_minutes=60,
            )
            base_utc = (
                solar_window.sunrise_utc
                if event_name == "sunrise"
                else solar_window.sunset_utc
            )
            candidate_utc = base_utc + timedelta(minutes=offset_minutes)
            if candidate_utc > reference_utc:
                return candidate_utc

        raise RuntimeError(f"Could not resolve next solar trigger for spec: {spec}")

    async def _run_solar_forecast(self, spec: str) -> None:
        try:
            await self._run_forecast()
        finally:
            if self._scheduler.running:
                self._schedule_next_solar_forecast(spec, reference_utc=datetime.now(timezone.utc))

    async def _run_forecast(self) -> None:
        if self._state.engine is None:
            logger.warning("forecast_skip_engine_missing")
            return
        if self._forecast_in_progress:
            logger.info("forecast_skip_in_progress")
            return
        self._forecast_in_progress = True
        try:
            panel_groups = await refresh_panel_groups_from_sfml(self._state)
            result = await self._state.engine.run_forecast(panel_groups)
            self._state.last_result = result
            self._state.last_result_at = result.generated_at
            logger.info(
                "scheduled_forecast_complete",
                total_p50=result.total_kwh_p50,
                lora=result.lora_status.value,
            )
        except Exception as exc:
            logger.error("scheduled_forecast_failed", error=str(exc), exc_info=True)
        finally:
            self._forecast_in_progress = False

    async def _run_finetune(self, force: bool = False) -> None:
        if self._finetune_in_progress:
            logger.info("finetune_skip_in_progress")
            return
        self._finetune_in_progress = True
        self._state.refinetune_status = "running"
        try:
            runner = self._state.extras.get("finetune_runner")
            if runner is None:
                logger.warning("finetune_skip_runner_missing")
                self._state.refinetune_status = "no_runner"
                return
            await runner(force=force)
            self._state.refinetune_status = "completed"
            self._state.last_refinetune_at = datetime.now(timezone.utc)
        except Exception as exc:
            logger.error("finetune_failed", error=str(exc), exc_info=True)
            self._state.refinetune_status = "failed"
        finally:
            self._finetune_in_progress = False


def _parse_hhmm(spec: str) -> tuple[int, int]:
    parts = spec.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time spec: {spec}")
    return int(parts[0]), int(parts[1])


def _is_solar_spec(spec: str) -> bool:
    spec = spec.strip()
    return spec.startswith("sunrise") or spec.startswith("sunset")


def _parse_solar_spec(spec: str) -> tuple[str, int]:
    spec = spec.strip()
    if spec.startswith("sunrise"):
        event_name = "sunrise"
        remainder = spec[len("sunrise") :]
    elif spec.startswith("sunset"):
        event_name = "sunset"
        remainder = spec[len("sunset") :]
    else:
        raise ValueError(f"Invalid solar time spec: {spec}")

    offset_minutes = 0
    if remainder.startswith("-"):
        offset_minutes = -int(remainder[1:] or "0")
    elif remainder.startswith("+"):
        offset_minutes = int(remainder[1:] or "0")
    elif remainder:
        raise ValueError(f"Invalid solar offset spec: {spec}")
    return event_name, offset_minutes


def _solar_job_id(spec: str) -> str:
    normalized = spec.strip().replace("+", "plus").replace("-", "minus")
    return f"forecast_dynamic_{normalized}"
