import sys
from pathlib import Path as _Path
_runtime_path = str(_Path(__file__).parent.parent)
if _runtime_path not in sys.path:
    sys.path.insert(0, _runtime_path)
try:
    import pyarmor_runtime_009810
except ImportError:
    pass

# ******************************************************************************
# @copyright (C) 2026 Zara-Toorox - Toorox ForeSight HA
# * This program is protected by a Proprietary Non-Commercial License.
# 1. Personal and Educational use only.
# 2. COMMERCIAL USE AND AI TRAINING ARE STRICTLY PROHIBITED.
# 3. Clear attribution to "Zara-Toorox" is required.
# * Full license terms: https://github.com/Zara-Toorox/toorox-foresight-ha/blob/main/LICENSE
# ******************************************************************************

"""Toorox ForeSight HA Add-on — ZARA brain extension for SFML. @zara"""

__version__ = "1.2.0"
