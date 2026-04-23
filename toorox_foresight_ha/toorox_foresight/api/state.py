"""Shared app-state container for the FastAPI server. @zara

Holds references to the singleton engine, database, blender etc. so that
route handlers can access them via dependency injection without globals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AppState:
    """Container for runtime-shared services. @zara"""

    settings: Any
    state_db: Any | None = None
    sfml_reader: Any | None = None
    astronomy: Any | None = None
    blender: Any | None = None
    lora_loader: Any | None = None
    engine: Any | None = None
    scheduler: Any | None = None
    last_result: Any | None = None
    last_result_at: datetime | None = None
    last_refinetune_requested_at: datetime | None = None
    last_refinetune_at: datetime | None = None
    refinetune_status: str = "idle"
    panel_groups: Any | None = None
    extras: dict[str, Any] = field(default_factory=dict)
