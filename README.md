<p align="center">
  <img src="docs/coffeebean.png" alt="OpenRoast" width="120" />
</p>

<h1 align="center">OpenRoast</h1>

<p align="center">
  <strong>Open-source, browser-based coffee roasting software.</strong><br/>
  Connect to your roaster from any device — tablet, phone, or desktop.
</p>

<p align="center">
  <a href="https://github.com/marcandrevigneault/openroast/actions/workflows/ci.yml"><img src="https://github.com/marcandrevigneault/openroast/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://codecov.io/gh/marcandrevigneault/openroast"><img src="https://codecov.io/gh/marcandrevigneault/openroast/branch/main/graph/badge.svg" alt="Coverage" /></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/SvelteKit-5-FF3E00?logo=svelte&logoColor=white" alt="SvelteKit 5" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
  <img src="https://img.shields.io/badge/code%20quality-A-brightgreen" alt="Code Quality A" />
</p>

---

## What it does

- **Real-time monitoring** — Live ET/BT charts over WebSocket
- **Multi-machine** — Control multiple roasters at once
- **Profiles** — Save, load, and replay roast curves
- **Auto detection** — CHARGE/DROP detected from BT curve analysis
- **Alarms** — Temperature and time-based alerts
- **Automation** — GPIO/relay control for doors, cooling trays, etc.
- **Protocol support** — Modbus RTU, serial, TCP

## Architecture

```
Browser (SvelteKit)  <— WebSocket + REST —>  Python (FastAPI)  <— Serial/Modbus —>  Roaster
```

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn openroast.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Running Tests

```bash
# Backend
cd backend && python -m pytest tests/ -v

# Frontend
cd frontend && npm test
```

## Contributing

See [CLAUDE.md](CLAUDE.md) for coding conventions, branch workflow, and module boundaries.

Every PR requires all tests passing, 90%+ backend coverage, and clean lints.

## License

MIT
