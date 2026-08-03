# ◢▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◣
# ▧ - Lunar Edge Games                                          ▧
# ▧ - Tor Meter                                                 ▧
# ▧▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▣▧
# ▧ - Module: App                                               ▧
# ▧ - Sub-Module: Constants                                     ▧
# ◥▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧▧◤

# Windows API constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
HOTKEY_ID = 1

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
