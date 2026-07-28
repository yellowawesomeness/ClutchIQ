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

- Add interactive 2D tactical replay
- Preserve normalized event data for:
  - player position
  - yaw
  - alive state
  - bomb events
  - utility events
  - exact tick timing
- Keep event normalization lossless enough for replay rendering and analysis
- Do not implement replay yet; keep current analysis fixture cleanup as the immediate task
