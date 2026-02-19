# OpenRoast

Browser-based coffee roasting software. Python/FastAPI backend + SvelteKit frontend.

## Architecture

- `backend/` — Python FastAPI server (hardware communication, business logic, WebSocket)
- `frontend/` — SvelteKit app (UI, real-time charts, PWA)
- `docs/` — Architecture docs, protocol specs, design decisions

## Development Commands

```bash
# Backend
cd backend && python -m pytest tests/ -v
cd backend && python -m pytest tests/ -v --cov=openroast --cov-report=term-missing
cd backend && uvicorn openroast.main:app --reload

# Frontend
cd frontend && npm run dev
cd frontend && npm test
cd frontend && npx playwright test

# Linting
cd backend && ruff check src/ tests/
cd frontend && npm run lint
```

## Branch Conventions

- `main` — protected, requires CI passing + PR approval
- `feature/<module>/<description>` — feature branches (e.g., `feature/drivers/modbus-rtu`)
- `fix/<module>/<description>` — bug fixes
- `test/<module>/<description>` — test-only branches

## Module Boundaries (for parallel agent work)

Agents should work within ONE module at a time to avoid merge conflicts.
Each module has a clear owner during a sprint:

| Module | Path | Description |
|--------|------|-------------|
| drivers | `backend/src/openroast/drivers/` | Machine communication (Modbus, serial) |
| core | `backend/src/openroast/core/` | Business logic (detection, session, PID, thermal) |
| api | `backend/src/openroast/api/` | REST API routes |
| ws | `backend/src/openroast/ws/` | WebSocket handlers for live data |
| models | `backend/src/openroast/models/` | Pydantic data models (shared contract) |
| components | `frontend/src/lib/components/` | UI components |
| stores | `frontend/src/lib/stores/` | Svelte state management |
| routes | `frontend/src/routes/` | SvelteKit pages |

## Testing Requirements

- **ALL code must have unit tests** — no exceptions
- Test file mirrors source: `backend/src/openroast/core/detection.py` → `backend/tests/unit/core/test_detection.py`
- **Minimum 90% coverage** target (enforced by CI)
- Tests must be **deterministic** — no random without seed, mock time/IO
- Use **fixtures and factories**, not raw object construction
- Integration tests for API endpoints and WebSocket connections
- Frontend: component tests with Vitest, E2E with Playwright

## Code Style

### Python (backend)
- **ruff** for linting and formatting
- Type hints on ALL functions and return types
- Pydantic models for all API request/response data
- Docstrings on public functions (Google style)
- No `# type: ignore` without explanation

### TypeScript (frontend)
- **Strict mode** enabled
- ESLint + Prettier
- No `any` types — use proper typing or `unknown`
- Svelte 5 runes syntax (`$state`, `$derived`, `$effect`)

## Commit Messages

Format: `<type>(<scope>): <description>`

Types: `feat`, `fix`, `test`, `refactor`, `docs`, `ci`, `chore`
Scopes: `drivers`, `core`, `api`, `ws`, `models`, `ui`, `ci`

Examples:
- `feat(drivers): add Modbus RTU base driver`
- `test(core): add BT break detection unit tests`
- `fix(ws): handle client disconnect during broadcast`

## CI/CD Pipeline

Every PR triggers:
1. Backend: lint → type-check → unit tests → coverage check
2. Frontend: lint → type-check → unit tests → E2E tests
3. Both must pass before merge is allowed

## Key Design Decisions

- **WebSocket for real-time data** — backend pushes temperature readings at sampling interval
- **REST for everything else** — profiles, config, machine management
- **SQLite for storage** — simple, portable, no external DB needed
- **Driver abstraction** — all roaster drivers implement `BaseDriver` protocol
- **Session-based roasting** — each roast is a `RoastSession` with full lifecycle
