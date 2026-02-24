<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { SvelteMap } from "svelte/reactivity";
  import type { MachineState } from "$lib/stores/machine";
  import {
    createInitialState,
    processMessage,
    processControlInput,
  } from "$lib/stores/machine";
  import type { RoastEventType, ServerMessage } from "$lib/types/ws-messages";
  import {
    createDashboardState,
    addMachine,
    removeMachine,
    updateLayout,
    type DashboardState,
    type LayoutConfig,
  } from "$lib/stores/dashboard";
  import {
    listMachines,
    connectMachine,
    disconnectMachine,
    deleteMachine,
    getMachine,
    type SavedMachine,
  } from "$lib/services/machine-api";
  import type { ControlConfig, ExtraChannelConfig } from "$lib/stores/machine";
  import { WSClient } from "$lib/services/ws-client";
  import { loadUIState, saveUIState } from "$lib/stores/persistence";
  import type { ChartOptions } from "$lib/stores/chart-options";
  import MachinePanel from "$lib/components/MachinePanel.svelte";
  import DashboardToolbar from "$lib/components/DashboardToolbar.svelte";
  import CatalogSelector from "$lib/components/CatalogSelector.svelte";
  import ToastContainer from "$lib/components/ToastContainer.svelte";
  import { addToast } from "$lib/stores/toast";
  import {
    evaluateSchedule,
    resetSchedule,
    type RoastSchedule,
  } from "$lib/stores/scheduler";
  import { saveProfile, type SaveProfileRequest } from "$lib/utils/api";

  let dashboard = $state<DashboardState>(createDashboardState());
  let machineStates = new SvelteMap<string, MachineState>();
  // eslint-disable-next-line svelte/prefer-svelte-reactivity -- not reactive, side-effect only
  let wsClients = new Map<string, WSClient>();
  let chartOptionsMap = $state<Record<string, ChartOptions>>({});
  let scheduleMap = new SvelteMap<string, RoastSchedule>();

  let showAddDialog = $state(false);

  let gridStyle = $derived(
    dashboard.layout.mode === "side-by-side"
      ? "grid-template-columns: repeat(2, 1fr)"
      : "grid-template-columns: 1fr",
  );

  function createWSClient(machineId: string): WSClient {
    const client = new WSClient(machineId, {
      onMessage: (msg: ServerMessage) => {
        const current = machineStates.get(machineId);
        if (!current) return;
        // Reset sync timestamp when backend clock resets to avoid
        // replaying stale data on reconnect
        if (
          msg.type === "state" &&
          (msg.state === "monitoring" || msg.state === "recording")
        ) {
          client.resetSyncTimestamp();
        }
        machineStates.set(machineId, processMessage(current, msg));
      },
      onStateChange: (wsState) => {
        const current = machineStates.get(machineId);
        if (!current) return;
        // Map WSClient state to driver state
        const driverState =
          wsState === "connected"
            ? "connected"
            : wsState === "connecting"
              ? "connecting"
              : wsState === "error"
                ? "error"
                : "disconnected";
        if (current.driverState !== driverState) {
          machineStates.set(machineId, { ...current, driverState });
        }
      },
    });
    wsClients.set(machineId, client);
    return client;
  }

  function toControlConfigs(machine: SavedMachine) {
    return (machine.controls ?? []).map((c) => ({
      name: c.name,
      channel: c.channel,
      min: c.min,
      max: c.max,
      step: c.step,
      unit: c.unit,
    }));
  }

  function toExtraChannelConfigs(machine: SavedMachine) {
    return (machine.extra_channels ?? []).map((ch) => ({
      name: (ch as { name?: string }).name ?? "Unknown",
    }));
  }

  async function handleAddMachine(machine: SavedMachine) {
    const id = machine.id;
    dashboard = addMachine(dashboard, { id, name: machine.name });
    machineStates.set(
      id,
      createInitialState(
        id,
        machine.name,
        toControlConfigs(machine),
        toExtraChannelConfigs(machine),
      ),
    );

    // Connect to the machine and start WebSocket
    try {
      await connectMachine(id);
      const client = createWSClient(id);
      client.connect();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Connection failed";
      const current = machineStates.get(id);
      if (current) {
        machineStates.set(id, {
          ...current,
          driverState: "error",
        });
        addToast(msg, "error", current.machineName);
      }
    }
  }

  async function handleRetryConnection(id: string) {
    const current = machineStates.get(id);
    if (!current) return;

    // Clear error state
    machineStates.set(id, {
      ...current,
      error: null,
      driverState: "connecting",
    });

    // If WSClient exists, force immediate reconnect
    const existingClient = wsClients.get(id);
    if (existingClient) {
      existingClient.retryNow();
      return;
    }

    // Otherwise retry the REST connection + create WSClient
    try {
      await connectMachine(id);
      const client = createWSClient(id);
      client.connect();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Connection failed";
      const state = machineStates.get(id);
      if (state) {
        machineStates.set(id, {
          ...state,
          driverState: "error",
        });
        addToast(msg, "error", state.machineName);
      }
    }
  }

  async function handleRemoveMachine(id: string) {
    // Disconnect WebSocket
    const client = wsClients.get(id);
    if (client) {
      client.disconnect();
      wsClients.delete(id);
    }

    // Disconnect machine from backend
    try {
      await disconnectMachine(id);
    } catch {
      // Best-effort disconnect
    }

    // Delete the saved machine file so it doesn't reappear on refresh
    try {
      await deleteMachine(id);
    } catch {
      // Best-effort delete
    }

    machineStates.delete(id);
    dashboard = removeMachine(dashboard, id);
  }

  function persistState() {
    saveUIState({
      version: 2,
      layout: dashboard.layout,
      chartOptions: chartOptionsMap,
    });
  }

  function handleLayoutChange(layout: Partial<LayoutConfig>) {
    dashboard = updateLayout(dashboard, layout);
    persistState();
  }

  function handleChartOptionsChange(id: string, options: ChartOptions) {
    chartOptionsMap = { ...chartOptionsMap, [id]: options };
    persistState();
  }

  function handleStart(id: string) {
    const client = wsClients.get(id);
    if (client) {
      client.send({ type: "command", action: "start_monitoring" });
    }
  }

  function handleStop(id: string) {
    const client = wsClients.get(id);
    if (!client) return;
    const state = machineStates.get(id);
    const action =
      state?.sessionState === "monitoring"
        ? "stop_monitoring"
        : "stop_recording";
    client.send({ type: "command", action });
  }

  function handleRecord(id: string) {
    const client = wsClients.get(id);
    if (client) {
      client.send({ type: "command", action: "start_recording" });
    }
  }

  function handleStopRecord(id: string) {
    const client = wsClients.get(id);
    if (client) {
      client.send({ type: "command", action: "stop_recording" });
    }
  }

  function handleMark(id: string, eventType: RoastEventType) {
    const client = wsClients.get(id);
    if (client) {
      client.send({
        type: "command",
        action: "mark_event",
        event_type: eventType,
      });
    }
  }

  async function handleSettingsSaved(id: string, machine: SavedMachine) {
    const current = machineStates.get(id);
    if (!current) return;

    const newControls: ControlConfig[] = toControlConfigs(machine);
    const newExtraChannels: ExtraChannelConfig[] =
      toExtraChannelConfigs(machine);

    // Update machine state with new config
    machineStates.set(id, {
      ...current,
      machineName: machine.name,
      controls: newControls,
      extraChannels: newExtraChannels,
    });

    // Update dashboard name
    const dm = dashboard.machines.find((m) => m.id === id);
    if (dm && dm.name !== machine.name) {
      dashboard = {
        ...dashboard,
        machines: dashboard.machines.map((m) =>
          m.id === id ? { ...m, name: machine.name } : m,
        ),
      };
    }

    // Reconnect backend driver so it picks up the new connection config
    const existingClient = wsClients.get(id);
    if (existingClient) {
      existingClient.disconnect();
      wsClients.delete(id);
      try {
        await disconnectMachine(id);
      } catch {
        // Best-effort disconnect
      }
      try {
        await connectMachine(id);
        const client = createWSClient(id);
        client.connect();
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Reconnection failed";
        const state = machineStates.get(id);
        if (state) {
          machineStates.set(id, { ...state, driverState: "error" });
          addToast(msg, "error", state.machineName);
        }
      }
    }
  }

  function handleReset(id: string) {
    const current = machineStates.get(id);
    if (!current) return;
    machineStates.set(id, {
      ...current,
      history: [],
      controlHistory: [],
      extraChannelHistory: [],
      events: [],
      currentTemp: null,
    });
    // Tell backend to reset session + clock so chart restarts at t=0
    const client = wsClients.get(id);
    if (client) {
      client.send({ type: "command", action: "reset" });
    }
  }

  function handleControl(
    id: string,
    channel: string,
    value: number,
    enabled?: boolean,
  ) {
    const client = wsClients.get(id);
    if (!client) return;

    // Record native-value control change immediately in state
    const state = machineStates.get(id);
    if (state) {
      machineStates.set(id, processControlInput(state, channel, value));
    }

    // Normalize native slider value to 0.0-1.0 using control config
    const ctrl = state?.controls.find((c) => c.channel === channel);
    const min = ctrl?.min ?? 0;
    const max = ctrl?.max ?? 100;
    const normalized = max !== min ? (value - min) / (max - min) : 0;

    client.send({
      type: "control",
      channel,
      value: normalized,
      ...(enabled !== undefined && { enabled }),
    });
  }

  async function handleSaveProfile(
    id: string,
    data: {
      name: string;
      beanName: string;
      beanWeight: number;
      chartImageBase64?: string;
    },
  ) {
    const state = machineStates.get(id);
    if (!state) return;

    // Filter out negative-timestamp data (pre-record monitoring tail)
    const recordedHistory = state.history.filter((p) => p.timestamp_ms >= 0);

    // Build controls from controlHistory (already in native slider values)
    const recordedControls: Record<string, [number, number][]> = {};
    for (const cp of state.controlHistory) {
      if (cp.timestamp_ms < 0) continue;
      for (const [ch, val] of Object.entries(cp.values)) {
        if (!recordedControls[ch]) recordedControls[ch] = [];
        recordedControls[ch].push([cp.timestamp_ms, val]);
      }
    }

    const req: SaveProfileRequest = {
      profile: {
        name: data.name,
        machine: state.machineName,
        temperatures: recordedHistory,
        events: state.events.map((e) => ({
          event_type: e.event_type,
          timestamp_ms: e.timestamp_ms,
          auto_detected: e.auto_detected,
        })),
        controls: recordedControls,
      },
      name: data.name,
      bean_name: data.beanName,
      bean_weight_g: data.beanWeight,
      chart_image_base64: data.chartImageBase64,
      schedule_name: scheduleMap.get(id)?.name ?? null,
    };

    try {
      await saveProfile(req);
      addToast("Profile saved", "info", state.machineName);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to save profile";
      addToast(msg, "error", state.machineName);
    }
  }

  function handleScheduleChange(id: string, s: RoastSchedule) {
    scheduleMap.set(id, s);
  }

  // Auto-start schedule when recording begins, auto-reset when recording ends.
  // Evaluate running schedules only during recording.
  $effect(() => {
    for (const [machineId, sched] of scheduleMap) {
      const state = machineStates.get(machineId);
      if (!state) continue;

      // Auto-start: schedule has steps and is idle → start when recording begins
      if (
        state.sessionState === "recording" &&
        sched.status === "idle" &&
        sched.steps.length > 0
      ) {
        scheduleMap.set(machineId, {
          ...resetSchedule(sched),
          status: "running",
        });
        continue;
      }

      // Auto-reset: recording ended while schedule was active
      if (
        state.sessionState !== "recording" &&
        (sched.status === "running" || sched.status === "paused")
      ) {
        scheduleMap.set(machineId, resetSchedule(sched));
        continue;
      }

      // Only evaluate during recording
      if (sched.status !== "running") continue;
      if (!state.currentTemp) continue;
      if (state.driverState !== "connected") continue;
      if (state.sessionState !== "recording") continue;

      const histLen = state.history.length;
      const prevTemp =
        histLen >= 2
          ? state.history[histLen - 2]
          : (state.history[histLen - 1] ?? state.currentTemp);

      const { schedule: updated, firedActions } = evaluateSchedule(
        sched,
        state.currentTemp.timestamp_ms,
        state.currentTemp.bt,
        state.currentTemp.et,
        prevTemp.bt,
        prevTemp.et,
      );

      if (firedActions.length > 0) {
        for (const action of firedActions) {
          handleControl(machineId, action.channel, action.value);
        }
        scheduleMap.set(machineId, updated);
      } else if (updated.status !== sched.status) {
        scheduleMap.set(machineId, updated);
      }
    }
  });

  async function loadSavedMachines() {
    try {
      const machines = await listMachines();
      for (const summary of machines) {
        try {
          const machine = await getMachine(summary.id);
          dashboard = addMachine(dashboard, {
            id: machine.id,
            name: machine.name,
          });
          machineStates.set(
            machine.id,
            createInitialState(
              machine.id,
              machine.name,
              toControlConfigs(machine),
              toExtraChannelConfigs(machine),
            ),
          );
        } catch {
          // Skip machines we can't load
        }
      }
    } catch {
      // Backend not available — that's OK, user can add machines later
    }
  }

  onMount(() => {
    // Restore persisted UI state
    const saved = loadUIState();
    if (saved) {
      dashboard = updateLayout(dashboard, saved.layout);
      chartOptionsMap = saved.chartOptions ?? {};
    }
    loadSavedMachines();
  });

  onDestroy(() => {
    for (const client of wsClients.values()) {
      client.disconnect();
    }
  });
</script>

<ToastContainer />

<div class="dashboard">
  <DashboardToolbar
    layout={dashboard.layout}
    machineCount={dashboard.machines.length}
    onaddmachine={() => (showAddDialog = true)}
    onlayoutchange={handleLayoutChange}
  />

  <div class="machine-grid" style={gridStyle}>
    {#each dashboard.machines as m (m.id)}
      {@const state = machineStates.get(m.id)}
      {#if state}
        <MachinePanel
          machine={state}
          chartOptions={chartOptionsMap[m.id]}
          onstart={() => handleStart(m.id)}
          onstop={() => handleStop(m.id)}
          onrecord={() => handleRecord(m.id)}
          onstoprecord={() => handleStopRecord(m.id)}
          onmark={(eventType) => handleMark(m.id, eventType)}
          oncontrol={(channel, value, enabled) =>
            handleControl(m.id, channel, value, enabled)}
          onchartoptionschange={(opts) => handleChartOptionsChange(m.id, opts)}
          onreset={() => handleReset(m.id)}
          onretry={() => handleRetryConnection(m.id)}
          onsettingssaved={(machine) => handleSettingsSaved(m.id, machine)}
          onremove={() => handleRemoveMachine(m.id)}
          schedule={scheduleMap.get(m.id)}
          onschedulechange={(s) => handleScheduleChange(m.id, s)}
          onsave={(data) => handleSaveProfile(m.id, data)}
        />
      {/if}
    {/each}
  </div>

  {#if dashboard.machines.length === 0}
    <div class="empty-state">
      <p>No machines added yet.</p>
      <button class="btn-start" onclick={() => (showAddDialog = true)}
        >+ Add Your First Machine</button
      >
    </div>
  {/if}

  <CatalogSelector
    open={showAddDialog}
    onadd={handleAddMachine}
    onclose={() => (showAddDialog = false)}
  />
</div>

<style>
  .dashboard {
    max-width: 1600px;
    margin: 0 auto;
  }

  .machine-grid {
    display: grid;
    gap: 16px;
  }

  .empty-state {
    text-align: center;
    padding: 80px 20px;
    color: #666;
  }

  .empty-state p {
    font-size: 1rem;
    margin-bottom: 16px;
  }

  .btn-start {
    background: #2e7d32;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-start:hover {
    background: #388e3c;
  }

  @media (max-width: 768px) {
    .machine-grid {
      grid-template-columns: 1fr !important;
      gap: 12px;
    }

    .empty-state {
      padding: 48px 16px;
    }
  }
</style>
