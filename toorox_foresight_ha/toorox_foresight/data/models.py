# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""ForeSight database models — clean schema for training and forecast data. @zara

Tables:
    hourly_records      — Main table: one row per hour with production + weather + astronomy
    weather_sources     — Raw weather data per source (Open-Meteo, DWD ICON, etc.)
    forecasts           — Generated forecast snapshots
    forecast_hours      — Hourly detail per forecast
    panel_groups        — Panel group configuration
    training_runs       — Training metadata and metrics
    calibration_state   — CQR and physics calibration state
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class HourlyRecord(Base):
    """One row per hour — the central training data table.
    Combines production, weather, and astronomy for a single hour. @zara"""
    __tablename__ = "hourly_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    hour = Column(Integer, nullable=False)
    day_of_year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    actual_kwh = Column(Float)
    actual_kwh_group1 = Column(Float)
    actual_kwh_group2 = Column(Float)
    actual_kwh_group3 = Column(Float)
    actual_kwh_group4 = Column(Float)

    temperature = Column(Float)
    ghi = Column(Float)
    dni = Column(Float)
    diffuse_radiation = Column(Float)
    wind_speed = Column(Float)
    humidity = Column(Float)
    rain = Column(Float)
    cloud_cover = Column(Float)
    cloud_cover_low = Column(Float)
    cloud_cover_mid = Column(Float)
    cloud_cover_high = Column(Float)
    pressure = Column(Float)
    visibility = Column(Float)
    snow_depth = Column(Float)

    sun_elevation = Column(Float)
    sun_azimuth = Column(Float)
    clear_sky_radiation = Column(Float)
    theoretical_max_kwh = Column(Float)
    daylight_hours = Column(Float)
    day_progress = Column(Float)
    hours_after_sunrise = Column(Float)
    hours_before_sunset = Column(Float)
    hours_since_solar_noon = Column(Float)
    air_mass = Column(Float)

    sensor_temperature = Column(Float)
    sensor_humidity = Column(Float)
    sensor_radiation = Column(Float)
    sensor_lux = Column(Float)

    is_daytime = Column(Boolean, default=False)
    is_outlier = Column(Boolean, default=False)
    inverter_clipped = Column(Boolean, default=False)
    mppt_throttled = Column(Boolean, default=False)
    snow_covered_panels = Column(Boolean, default=False)
    data_quality = Column(Float, default=1.0)

    source = Column(String(20), default="ha")
    imported_from = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("timestamp", name="uq_hourly_timestamp"),
        Index("ix_hourly_daytime", "is_daytime", "is_outlier"),
    )


class WeatherSource(Base):
    """Raw weather data per source — for AI blending. @zara"""
    __tablename__ = "weather_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    source_name = Column(String(50), nullable=False)
    forecast_hour = Column(Integer)

    temperature = Column(Float)
    ghi = Column(Float)
    dni = Column(Float)
    diffuse_radiation = Column(Float)
    gti = Column(Float)
    wind_speed = Column(Float)
    humidity = Column(Float)
    rain = Column(Float)
    cloud_cover = Column(Float)
    cloud_cover_low = Column(Float)
    cloud_cover_mid = Column(Float)
    cloud_cover_high = Column(Float)
    pressure = Column(Float)
    visibility = Column(Float)
    snow_depth = Column(Float)
    weather_code = Column(Integer)

    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_weather_source_ts", "timestamp", "source_name"),
    )


class Forecast(Base):
    """A single forecast snapshot (one trigger = one forecast). @zara"""
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(DateTime, nullable=False, index=True)
    forecast_type = Column(String(20), nullable=False)
    horizon_hours = Column(Integer, default=72)
    total_kwh_p10 = Column(Float)
    total_kwh_p50 = Column(Float)
    total_kwh_p90 = Column(Float)
    model_version = Column(String(20))
    confidence = Column(String(10))
    weather_sources_used = Column(JSON)
    computation_time_ms = Column(Integer)

    hours = relationship("ForecastHour", back_populates="forecast", cascade="all, delete-orphan")


class ForecastHour(Base):
    """Single hour within a forecast. @zara"""
    __tablename__ = "forecast_hours"

    id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_id = Column(Integer, ForeignKey("forecasts.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    hour_offset = Column(Integer, nullable=False)

    p10 = Column(Float)
    p50 = Column(Float)
    p90 = Column(Float)
    p10_group1 = Column(Float)
    p50_group1 = Column(Float)
    p10_group2 = Column(Float)
    p50_group2 = Column(Float)

    solar_elevation = Column(Float)
    clear_sky_power = Column(Float)
    weather_condition = Column(String(30))
    frost_risk = Column(Boolean, default=False)
    fog_risk = Column(Boolean, default=False)
    mppt_throttle = Column(Boolean, default=False)

    forecast = relationship("Forecast", back_populates="hours")


class PanelGroup(Base):
    """Panel group configuration. @zara"""
    __tablename__ = "panel_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    azimuth = Column(Float, nullable=False)
    tilt = Column(Float, nullable=False)
    capacity_kwp = Column(Float, nullable=False)
    module_count = Column(Integer)
    efficiency_stc = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrainingRun(Base):
    """Training run metadata and metrics. @zara"""
    __tablename__ = "training_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    epochs_completed = Column(Integer)
    best_val_loss = Column(Float)
    train_loss_final = Column(Float)
    val_loss_final = Column(Float)
    learning_rate = Column(Float)
    batch_size = Column(Integer)
    training_samples = Column(Integer)
    validation_samples = Column(Integer)
    model_params = Column(Integer)
    duration_seconds = Column(Float)
    checkpoint_path = Column(String(200))
    notes = Column(Text)


class CalibrationState(Base):
    """CQR and physics calibration state. @zara"""
    __tablename__ = "calibration_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calibration_type = Column(String(30), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
    parameters = Column(JSON)
    coverage_achieved = Column(Float)
    samples_used = Column(Integer)
