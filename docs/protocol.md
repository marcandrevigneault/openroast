# OpenRoast Real-Time Communication Protocol

## Why Not REST-Only?

REST can only simulate server push via polling. For 3 machines at 1-second sampling,
that means 3 HTTP requests/second — each carrying ~500 bytes of HTTP headers for ~50
bytes of payload. Over a 15-minute roast: 2,700 requests and ~1.35 MB of header overhead
for ~135 KB of actual data.

Polling also introduces 0–1000ms jitter, making temperature curves visually jerky and
RoR calculations noisy. Events like CHARGE and DROP arrive up to one polling interval late.

## Protocol Split

| Pattern | Protocol | Why |
|---------|----------|-----|
| Continuous push (temps, replay) | **WebSocket** | Persistent, bidirectional, minimal framing |
| Sporadic push (events, alarms) | **WebSocket** | Same connection, instant delivery |
| Control commands (sliders) | **WebSocket** | Sub-200ms, no HTTP handshake per command |
| CRUD (profiles, machines, config) | **REST** | Cacheable, idempotent, easy to test |
| Session lifecycle (start/stop) | **REST + WS** | Both paths, same backend methods |

## Connection Topology: One WebSocket Per Machine

```
Browser Tab
  ├── WS: /ws/live/machine-a  <──>  Backend  <──>  Driver A
  ├── WS: /ws/live/machine-b  <──>  Backend  <──>  Driver B
  └── REST: /api/...           <──>  REST handlers
```

Per-machine connections provide fault isolation (Machine B crashing doesn't affect A),
lifecycle simplicity (open panel = open WS, close panel = close WS), and natural
backpressure. At 1-4 machines, connection count is trivial.

## Message Schema

Every WebSocket message is JSON with a `type` discriminator field.

### Server → Client Messages

#### `temperature` — periodic reading at sampling interval
```json
{
  "type": "temperature",
  "timestamp_ms": 45000,
  "et": 210.5,
  "bt": 185.3,
  "et_ror": 8.2,
  "bt_ror": 12.4,
  "extra_channels": {"inlet_temp": 305.0}
}
```
- All temperatures in **Celsius** — frontend converts based on user preference
- RoR computed server-side (single source of truth)

#### `event` — roast event detected
```json
{
  "type": "event",
  "event_type": "CHARGE",
  "timestamp_ms": 5000,
  "auto_detected": true,
  "bt_at_event": 155.2,
  "et_at_event": 210.5
}
```
Event types: `CHARGE`, `DRY_END`, `FCs`, `FCe`, `SCs`, `SCe`, `DROP`, `COOL`, `TP`

#### `state` — session state transition
```json
{
  "type": "state",
  "state": "recording",
  "previous_state": "monitoring"
}
```
States: `idle`, `monitoring`, `recording`, `finished`

#### `alarm` — alarm triggered
```json
{
  "type": "alarm",
  "alarm_id": "high_bt",
  "message": "BT exceeded 230C",
  "severity": "warning",
  "timestamp_ms": 120000,
  "bt": 231.2,
  "et": 285.0
}
```
Severities: `info`, `warning`, `critical`

#### `replay` — profile replay data point
```json
{
  "type": "replay",
  "timestamp_ms": 3000,
  "et": 200.1,
  "bt": 150.8,
  "et_ror": 6.5,
  "bt_ror": 10.2,
  "controls": {"burner": 0.7, "airflow": 0.5},
  "progress_pct": 12.5,
  "total_duration_ms": 780000
}
```

#### `control_ack` — control command acknowledgement
```json
{
  "type": "control_ack",
  "channel": "burner",
  "value": 0.8,
  "applied": true,
  "message": ""
}
```

#### `error` — non-fatal error
```json
{
  "type": "error",
  "code": "DRIVER_READ_FAILED",
  "message": "Modbus timeout reading BT register",
  "recoverable": true
}
```

#### `connection` — driver state change
```json
{
  "type": "connection",
  "driver_state": "connected",
  "driver_name": "Modbus RTU",
  "message": ""
}
```

### Client → Server Messages

#### `control` — set slider value
```json
{"type": "control", "channel": "burner", "value": 0.8}
```
Channels: `burner`, `airflow`, `fan`, or driver-specific names. Value: 0.0–1.0 normalized.

#### `command` — session control
```json
{"type": "command", "action": "start_recording"}
{"type": "command", "action": "mark_event", "event_type": "FCs"}
```
Actions: `start_monitoring`, `start_recording`, `stop_recording`, `mark_event`, `reset`, `sync`

#### `replay_control` — replay playback
```json
{"type": "replay_control", "action": "start", "profile_id": "abc-123", "speed": 1.0}
```
Actions: `start`, `pause`, `resume`, `stop`, `seek`

## REST API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/machines` | List configured machines |
| `POST` | `/api/machines` | Add a machine |
| `GET` | `/api/machines/{id}` | Get machine config |
| `PUT` | `/api/machines/{id}` | Update machine config |
| `DELETE` | `/api/machines/{id}` | Remove a machine |
| `POST` | `/api/machines/{id}/connect` | Connect to hardware |
| `POST` | `/api/machines/{id}/disconnect` | Disconnect from hardware |
| `GET` | `/api/machines/{id}/session` | Get current session state |
| `GET` | `/api/profiles` | List saved profiles |
| `POST` | `/api/profiles` | Save a profile |
| `GET` | `/api/profiles/{id}` | Get a profile |
| `DELETE` | `/api/profiles/{id}` | Delete a profile |

## Reconnection Strategy

- **Exponential backoff**: 1s → 2s → 4s → ... → 30s max, with 30% jitter
- **Unlimited retries**: roasts can last 20+ minutes; connection must survive
- **Ring buffer sync**: server keeps last 60s of data per machine; on reconnect, client sends `{"type":"command","action":"sync","last_timestamp_ms":45000}` and server replays buffered points
- **Tab backgrounding**: on `visibilitychange`, check gap and sync if needed
- **Session survives disconnect**: sessions are server-owned, not tied to client connections

## Error Codes

| Code | Meaning | Recoverable |
|------|---------|-------------|
| `DRIVER_READ_FAILED` | Hardware read timeout | Yes |
| `DRIVER_WRITE_FAILED` | Control command failed | Yes |
| `DRIVER_DISCONNECTED` | Hardware connection lost | Yes |
| `INVALID_STATE_TRANSITION` | Command invalid for state | Yes |
| `INVALID_MESSAGE` | Malformed client message | Yes |
| `MACHINE_NOT_FOUND` | machine_id doesn't exist | No |
| `SESSION_LOCKED` | Another client controlling | Yes (read-only) |

## Typical Roast Sequence

```
Browser                    Backend                    Hardware
  |                          |                          |
  |-- POST /machines/m1/connect -->                     |
  |<- 200 OK                 |-- driver.connect() ---->|
  |                          |<- connected -------------|
  |-- WS /ws/live/m1 ------->|                          |
  |<- {connection: connected} |                          |
  |-- {command: start_monitoring} -->                    |
  |<- {state: monitoring}     |                          |
  |<- {temperature: ...}      |<- read_temperatures() ->|  [every 1-3s]
  |-- {command: start_recording} -->                     |
  |<- {state: recording}      |                          |
  |<- {event: CHARGE, auto}   |  [BT break detected]    |
  |-- {control: burner=0.7} ->|-- write_control() ----->|
  |<- {control_ack: applied}  |                          |
  |<- {event: FCs, auto}      |                          |
  |-- {command: mark_event DROP} -->                     |
  |<- {event: DROP, manual}   |                          |
  |-- {command: stop_recording} -->                      |
  |<- {state: finished}       |                          |
  |-- POST /profiles (save) ->|                          |
  |<- 201 Created             |                          |
```
