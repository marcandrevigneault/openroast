# OpenRoast

Browser-based coffee roasting software. Connect to your roaster from any device — tablet, phone, or desktop.

## Features (Roadmap)

- **Real-time monitoring** — Live ET/BT charts via WebSocket
- **Multi-machine support** — Monitor and control multiple roasters simultaneously
- **Profile management** — Save, load, and replay roast profiles
- **Auto detection** — Automatic CHARGE/DROP detection via BT curve analysis
- **Alarm system** — Configurable temperature and time-based alarms
- **Automation** — GPIO/relay control for doors, cooling trays, etc.
- **Manufacturer support** — Modbus RTU, serial, TCP protocols

## Architecture

```
Browser (SvelteKit)  ←— WebSocket + REST —→  Python Backend (FastAPI)  ←— Serial/Modbus —→  Roaster
```

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
uvicorn openroast.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm test
npm run dev
```

## Development

See [CLAUDE.md](CLAUDE.md) for coding conventions, branch workflow, and module boundaries.

Every PR requires:
- All tests passing (backend + frontend)
- 90%+ code coverage (backend)
- Lint clean (ruff + eslint)

## License

MIT
