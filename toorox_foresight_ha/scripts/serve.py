"""Container entry point — runs the FastAPI app via uvicorn. @zara"""

from __future__ import annotations

import os
import sys

import uvicorn


def main() -> int:
    from toorox_foresight.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "toorox_foresight.api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        loop="uvloop",
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
