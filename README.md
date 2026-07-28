# TorMeter

A semi-transparent, click-through overlay application built with Python and PyQt6. Designed to display parsed data and summary information on top of other applications without interrupting them.

---

## Requirements

- Python 3.x (3.11 or 3.12 recommended)
- Windows (click-through relies on `WS_EX_TRANSPARENT` via `ctypes`)

---

## Setup

### 1. Create the virtual environment

```powershell
python -m venv .venv
```

### 2. Install dependencies

```powershell
.venv\Scripts\pip install -r requirements.txt
```

### 3. Run the application

```powershell
.venv\Scripts\python main.py
```

---

## Building an Executable

PyInstaller is used to package the app into a standalone `.exe`.

```powershell
.venv\Scripts\pyinstaller TorMeter.spec
```

Output: `dist\TorMeter.exe`

- The `build\` directory is intermediate and can be safely deleted after building.
- The spec file (`TorMeter.spec`) controls build options: single-file mode, no console window, and required PyQt6 hidden imports.

### Updating the build after dependency changes

```powershell
.venv\Scripts\pip freeze > requirements.txt
.venv\Scripts\pyinstaller TorMeter.spec
```

---

## GitHub Readiness

This repository is set up to track source code and build configuration, while ignoring machine-local and generated files.

Ignored by `.gitignore`:

- `.venv/`
- `.vscode/`
- `__pycache__/`
- `build/` and `dist/`
- `data/UserPreferences.json`
- `data/combatlogs/*.txt`
- `err_log.txt`

Safe to commit:

- `main.py`
- `app/`
- `requirements.txt`
- `TorMeter.spec`
- `README.md`

---

## Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| PyQt6 | 6.11.0 | UI framework (overlay window, widgets) |
| PyQt6-Qt6 | 6.11.1 | Qt6 runtime binaries |
| PyQt6-sip | 13.11.1 | Python/C++ binding layer |
| PyInstaller | 6.20.0 | Build and export to executable |

---

## Architecture Notes

### Overlay Window (`main.py`)

- `FramelessWindowHint` — removes title bar and borders
- `WindowStaysOnTopHint` — keeps overlay above all other windows
- `WA_TranslucentBackground` — true OS-composited transparency
- `setWindowOpacity(0.75)` — semi-transparent rendering
- `Qt.WindowType.Tool` — hides the window from the taskbar

### Click-Through

Click-through is achieved on Windows via `ctypes` by setting the `WS_EX_TRANSPARENT | WS_EX_LAYERED` extended window styles on the native HWND after the window is shown:

```python
ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
```

> **Note:** This is Windows-only. Cross-platform click-through requires platform-specific handling (e.g., `NSWindow` on macOS, X11 shape extension on Linux).

### Recommended Pattern for Data Updates

Use a background thread for data parsing and feed updates to the UI via `QTimer` on the main thread. Direct UI updates from non-main threads are not safe in Qt.

### Combat Calculations: Where, How, and Update Flow

#### 1) Where calculations are performed

- `app/combat_session.py`
  - `PlayerFightStats.dps(duration_s)`
  - `PlayerFightStats.hps(duration_s)`
  - `PlayerFightStats.dtps(duration_s)`
  - `PlayerFightStats.crit_rate`
  - `_accumulate_stats(fight, event)` updates raw per-event totals.
- `app/log_watcher.py`
  - `_ingest(events)` performs incremental live accumulation via `_accumulate_stats`.
  - Emits `fight_updated` and `fight_closed` so overlays recalculate and repaint.
- `app/overlays_core/player_list/base.py`
  - `_on_fight_updated(fight)` calculates overlay-specific live values and scores.
- `app/overlays_core/player_list/windows.py`
  - `SummaryWindow._on_fight_updated(fight)` calculates combined tri-stat scores.
- `app/overlays_charts/stats.py`
  - `_get_stat(...)` chooses the stat formula for charts (DPS/HPS/DTPS/Damage/Heal).

#### 2) How calculations are performed

- Raw totals (updated per combat log event):
  - `damage_out`, `damage_in`, `heal_out`, `heal_in`
  - `hit_count`, `crit_count`
- Rate formulas:
  - `DPS = damage_out / duration_s`
  - `HPS = heal_out / duration_s`
  - `DTPS = damage_in / duration_s`
  - `Crit% = crit_count / hit_count`
- Overlay score behavior in player list overlays:
  - `Average + Total` enabled: score combines rate + raw total.
  - `Average` only: score uses only rate.
  - `Total` only: score uses only raw totals.

#### 3) How calculations are updated live

- New log lines are parsed in `LogWatcher._poll()` and ingested in `LogWatcher._ingest()`.
- On every ingest batch, the watcher emits `fight_updated(current_fight)`.
- Overlays receive that signal and recompute all displayed values from current fight stats.
- Local-player footer is updated with current live DPS/HPS/DTPS/Crit values.

#### 4) Live Average fix (stat-over-time)

- While a fight is open and no new log lines arrive, `log_watcher.py` now performs idle-tick live updates.
- It projects elapsed live time from the most recent event and advances fight duration before emitting `fight_updated`.
- This keeps Average (rate-over-time) values current between events instead of appearing frozen.
- Grace-ended fights now also close on idle ticks after grace timeout, even with no trailing events.

#### 5) Player display retention (configurable)

- Player rows are retained for a configurable minimum window before dropping from display.
- Configure this in Overlay Master: `Keep Players On Display (sec)`.
- Supported range is `30` to `600` seconds (default `120`).

---

## Troubleshooting

### `python` not found / Microsoft Store stub
- Check what Windows is resolving first:

  ```powershell
  Get-Command python
  where.exe python
  ```

- If the result points to `WindowsApps\python.exe`, disable the Store alias under `Settings > Apps > Advanced app settings > App execution aliases`.
- Install Python from [python.org](https://www.python.org/downloads/) and make sure **"Add python.exe to PATH"** is checked during setup.
- After installing, open a new terminal and verify with `python --version` or `py --version`.
- The project can still be run through the virtual environment once it exists:

  ```powershell
  .venv\Scripts\python main.py
  ```

### PyInstaller missing PyQt6 plugins at runtime
- Ensure `TorMeter.spec` includes the hidden imports:
  ```python
  hiddenimports=['PyQt6.sip', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets']
  ```

### Window not transparent
- Confirm `WA_TranslucentBackground` is set **before** `show()` is called.
- Ensure the compositor is active (disable GPU acceleration workarounds are not needed on modern Windows).

### Overlay appears behind other windows
- Verify `WindowStaysOnTopHint` is present in `setWindowFlags(...)`.
- Some full-screen exclusive applications (e.g., games in exclusive fullscreen mode) will always render above system overlays. Use borderless windowed mode in the target application.
