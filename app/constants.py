# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: Constants                                     ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Resolve a bundled asset path for both dev and frozen (PyInstaller) runs."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / relative


ICON_PATH = resource_path("assets/icons/TorMeter.png")

# Windows API constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B
HOTKEY_ID = 1

# SetWindowPos constants (used to force windows back to the topmost z-order)
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

# Debugging
DEBUG = True

# Format Number
def fmt_num(value: float) -> str:
    """
    Format a numeric value for display in overlays.

    < 100,000  → comma-separated integer (e.g. 1,234 or 99,999)
    < 1,000,000 → e.g. 123.4K
    < 1,000,000,000 → e.g. 1.2M
    < 1,000,000,000,000 → e.g. 3.4B
    otherwise  → e.g. 1.2T
    """
    
    v = abs(value)
    if v < 100_000:
        return f"{value:,.0f}"
    
    if v < 1_000_000:
        return f"{value / 1_000:.1f}K"
    
    if v < 1_000_000_000:
        return f"{value / 1_000_000:.1f}M"
    
    if v < 1_000_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    
    return f"{value / 1_000_000_000_000:.1f}T"
