# ClutchIQ

A minimal PySide6 desktop interface with a black-and-yellow theme.

## Requirements

- Python 3.10 or newer

## Run

Create and activate a virtual environment, install the dependency, and launch the app:

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Roadmap

The immediate priority is analysis fixture cleanup. Replay UI implementation is not yet in scope.

### Timeline & Replay Compatibility

The timeline will be the single source of truth for replay, analytics, and future annotations.

- Preserve every event at its exact source tick without rounding or reconstructing timing.
- Provide a stable, extensible public timeline API that can evolve through backward-compatible additions.
- Use non-lossy timeline models that retain source data required by future consumers.
- Keep raw demo events separate from derived analytics.
- Derive replay state and analytics from the timeline rather than maintaining parallel representations.
- Extend timeline support incrementally to include:
  - player positions
  - facing direction
  - alive/dead state
  - team and side
  - bomb events
  - utility events
  - damage events
  - optional economy snapshots
  - future AI annotations that reference timeline ticks without modifying source events

#### Future Features Enabled

- Interactive 2D tactical replay
- Heatmaps
- Rotation visualization
- Trade detection
- KAST
- Clutch analysis
- Utility analysis
- AI coaching
- Historical player improvement tracking
