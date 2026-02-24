<script lang="ts">
  import type { MachineState } from "$lib/stores/machine";
  import type { RoastEventType } from "$lib/types/ws-messages";
  import {
    createChartOptions,
    smoothRor,
    type ChartOptions,
  } from "$lib/stores/chart-options";
  import { addToast } from "$lib/stores/toast";
  import TemperatureDisplay from "./TemperatureDisplay.svelte";
  import RoastChart from "./RoastChart.svelte";
  import ControlChart from "./ControlChart.svelte";
  import ChartOptionsMenu from "./ChartOptionsMenu.svelte";
  import ControlSlider from "./ControlSlider.svelte";
  import EventButtons from "./EventButtons.svelte";
  import SessionControls from "./SessionControls.svelte";
  import ConnectionStatus from "./ConnectionStatus.svelte";
  import ExtraChannelsBar from "./ExtraChannelsBar.svelte";
  import SaveProfileForm from "./SaveProfileForm.svelte";
  import MachineSettingsPanel from "./MachineSettingsPanel.svelte";
  import SchedulerDialog from "./SchedulerDialog.svelte";
  import type { SavedMachine } from "$lib/services/machine-api";
  import { createSchedule, type RoastSchedule } from "$lib/stores/scheduler";

  interface Props {
    machine: MachineState;
    chartOptions?: ChartOptions;
    onstart?: () => void;
    onstop?: () => void;
    onrecord?: () => void;
    onstoprecord?: () => void;
    onmark?: (eventType: RoastEventType) => void;
    oncontrol?: (channel: string, value: number, enabled?: boolean) => void;
    onchartoptionschange?: (options: ChartOptions) => void;
    onreset?: () => void;
    onremove?: () => void;
    onretry?: () => void;
    onsettingssaved?: (machine: SavedMachine) => void;
    onsave?: (data: {
      name: string;
      beanName: string;
      beanWeight: number;
    }) => void;
    schedule?: RoastSchedule;
    onschedulechange?: (schedule: RoastSchedule) => void;
  }

  let {
    machine,
    chartOptions,
    onstart,
    onstop,
    onrecord,
    onstoprecord,
    onmark,
    oncontrol,
    onchartoptionschange,
    onreset,
    onremove,
    onretry,
    onsettingssaved,
    onsave,
    schedule,
    onschedulechange,
  }: Props = $props();

  const CONTROL_COLORS = [
    "#e6c229",
    "#66bb6a",
    "#ab47bc",
    "#26c6da",
    "#ef5350",
    "#8d6e63",
  ];

  let sliderValues = $state<Record<string, number>>({});
  let draggingChannels = $state<Record<string, boolean>>({});
  let cooldownUntil = $state<Record<string, number>>({});
  let controlsEnabled = $state<Record<string, boolean>>({});
  let lastControlValues = $state<Record<string, number>>({});
  const READBACK_COOLDOWN_MS = 1500;

  // Sync slider values from extra channel read-backs, but skip channels
  // the user is actively dragging or that are within the post-drag cooldown
  // to prevent jitter from lagging hardware read-backs.
  $effect(() => {
    const now = Date.now();
    for (const ctrl of machine.controls) {
      const readback = machine.currentExtraChannels[ctrl.name];
      if (readback !== undefined) {
        const isDragging = draggingChannels[ctrl.channel];
        const inCooldown = (cooldownUntil[ctrl.channel] ?? 0) > now;
        if (!isDragging && !inCooldown) {
          sliderValues[ctrl.channel] = readback;
        }
      }
    }
  });

  let saving = $state(false);
  let saved = $state(false);
  let settingsOpen = $state(false);
  let schedulerOpen = $state(false);
  let localSchedule = $state(createSchedule());
  let effectiveSchedule = $derived(schedule ?? localSchedule);
  let scheduleFiredCount = $derived(
    effectiveSchedule.steps.filter((s) => s.fired).length,
  );
  let scheduleEnabledCount = $derived(
    effectiveSchedule.steps.filter((s) => s.enabled).length,
  );

  function handleScheduleChange(s: RoastSchedule) {
    localSchedule = s;
    onschedulechange?.(s);
  }
  let lastToastedError = $state<string | null>(null);

  // svelte-ignore state_referenced_locally
  const initControlChannels = machine.controls.map(
    (c: { channel: string }) => c.channel,
  );
  // svelte-ignore state_referenced_locally
  const initExtraChannelNames = machine.extraChannels.map(
    (c: { name: string }) => c.name,
  );
  let localChartOptions = $state(
    createChartOptions(initControlChannels, initExtraChannelNames),
  );
  let effectiveOptions = $derived(chartOptions ?? localChartOptions);

  function handleChartOptionsChange(opts: ChartOptions) {
    localChartOptions = opts;
    onchartoptionschange?.(opts);
  }

  let isConnected = $derived(machine.driverState === "connected");
  let showRetryButton = $derived(
    machine.driverState === "error" || machine.driverState === "disconnected",
  );

  // Smoothed RoR for the header temperature display
  let smoothedHeaderEtRor = $derived(() => {
    const w = effectiveOptions.rorSmoothing;
    if (w <= 1 || machine.history.length === 0)
      return machine.currentTemp?.et_ror ?? null;
    const rors = machine.history.map((p) => p.et_ror);
    const smoothed = smoothRor(rors, w);
    return smoothed[smoothed.length - 1] ?? null;
  });
  let smoothedHeaderBtRor = $derived(() => {
    const w = effectiveOptions.rorSmoothing;
    if (w <= 1 || machine.history.length === 0)
      return machine.currentTemp?.bt_ror ?? null;
    const rors = machine.history.map((p) => p.bt_ror);
    const smoothed = smoothRor(rors, w);
    return smoothed[smoothed.length - 1] ?? null;
  });
  let showSaveForm = $derived(
    machine.sessionState === "finished" && machine.history.length > 0 && !saved,
  );

  // Dispatch machine errors as toast notifications
  $effect(() => {
    if (machine.error && machine.error !== lastToastedError) {
      addToast(machine.error, "error", machine.machineName);
      lastToastedError = machine.error;
    } else if (!machine.error) {
      lastToastedError = null;
    }
  });

  function handleSave(data: {
    name: string;
    beanName: string;
    beanWeight: number;
  }) {
    saving = true;
    onsave?.(data);
    saving = false;
    saved = true;
  }
</script>

<div class="machine-panel">
  <!-- Compact header: name, temps, status, remove -->
  <div class="panel-header">
    <div class="header-row-top">
      <h2 class="machine-name">{machine.machineName}</h2>
      <div class="header-actions">
        <ConnectionStatus
          driverState={machine.driverState}
          sessionState={machine.sessionState}
        />
        {#if showRetryButton && onretry}
          <button
            class="btn-retry-header"
            onclick={onretry}
            title="Retry connection">&#8635;</button
          >
        {/if}
        <button
          class="btn-settings"
          onclick={() => (settingsOpen = true)}
          title="Machine settings"
        >
          &#9881;
        </button>
        {#if onremove}
          <button class="btn-remove" onclick={onremove} title="Remove machine"
            >✕</button
          >
        {/if}
      </div>
    </div>
    <div class="header-temps">
      <TemperatureDisplay
        label="ET"
        value={machine.currentTemp?.et ?? null}
        ror={smoothedHeaderEtRor()}
        color="#ff7043"
        compact
      />
      <TemperatureDisplay
        label="BT"
        value={machine.currentTemp?.bt ?? null}
        ror={smoothedHeaderBtRor()}
        color="#42a5f5"
        compact
      />
    </div>
  </div>

  <!-- Temperature chart -->
  <div class="chart-section">
    <RoastChart history={machine.history} options={effectiveOptions} />
    <div class="chart-toolbar">
      {#if onreset}
        <button class="btn-chart-tool" onclick={onreset} title="Reset chart"
          >&#8634;</button
        >
      {/if}
      <ChartOptionsMenu
        options={effectiveOptions}
        controls={machine.controls}
        extraChannels={machine.extraChannels}
        onchange={handleChartOptionsChange}
      />
    </div>
  </div>

  <!-- Controls chart -->
  <ControlChart
    history={machine.history}
    controlHistory={machine.controlHistory}
    controls={machine.controls}
    extraChannelHistory={machine.extraChannelHistory}
    extraChannels={machine.extraChannels}
    options={effectiveOptions}
  />

  <!-- Extra channels bar -->
  <ExtraChannelsBar
    channels={machine.extraChannels}
    values={machine.currentExtraChannels}
  />

  <!-- Session controls + event buttons in one compact row -->
  <div class="actions-row">
    <SessionControls
      sessionState={machine.sessionState}
      {onstart}
      {onstop}
      {onrecord}
      {onstoprecord}
    />
    <EventButtons disabled={true} events={machine.events} {onmark} />
    {#if machine.controls.length > 0}
      <button
        class="btn-scheduler"
        class:active={effectiveSchedule.status === "running"}
        onclick={() => (schedulerOpen = true)}
        title="Roast schedule"
      >
        &#128337; Schedule
        {#if effectiveSchedule.steps.length > 0}
          <span class="schedule-badge"
            >({scheduleFiredCount}/{scheduleEnabledCount})</span
          >
        {/if}
      </button>
    {/if}
  </div>

  <!-- Controls -->
  {#if machine.controls.length > 0}
    <div class="controls-section">
      <div class="controls-grid">
        {#each machine.controls as ctrl (ctrl.channel)}
          <ControlSlider
            label={ctrl.name}
            value={sliderValues[ctrl.channel] ?? ctrl.min}
            min={ctrl.min}
            max={ctrl.max}
            step={ctrl.step}
            unit={ctrl.unit}
            color={CONTROL_COLORS[
              machine.controls.indexOf(ctrl) % CONTROL_COLORS.length
            ]}
            disabled={!isConnected}
            enabled={controlsEnabled[ctrl.channel] ?? true}
            ondragstart={() => {
              draggingChannels[ctrl.channel] = true;
            }}
            ondragend={() => {
              draggingChannels[ctrl.channel] = false;
              cooldownUntil[ctrl.channel] = Date.now() + READBACK_COOLDOWN_MS;
            }}
            onchange={(v) => {
              sliderValues[ctrl.channel] = v;
              cooldownUntil[ctrl.channel] = Date.now() + READBACK_COOLDOWN_MS;
              oncontrol?.(ctrl.channel, v);
            }}
            ontoggle={(on) => {
              controlsEnabled[ctrl.channel] = on;
              if (on) {
                const restored =
                  lastControlValues[ctrl.channel] ??
                  sliderValues[ctrl.channel] ??
                  ctrl.min;
                sliderValues[ctrl.channel] = restored;
                oncontrol?.(ctrl.channel, restored, true);
              } else {
                lastControlValues[ctrl.channel] =
                  sliderValues[ctrl.channel] ?? ctrl.min;
                oncontrol?.(
                  ctrl.channel,
                  sliderValues[ctrl.channel] ?? ctrl.min,
                  false,
                );
              }
            }}
          />
        {/each}
      </div>
    </div>
  {/if}

  {#if showSaveForm}
    <SaveProfileForm onsave={handleSave} {saving} {saved} />
  {/if}

  <MachineSettingsPanel
    machineId={machine.machineId}
    open={settingsOpen}
    onclose={() => (settingsOpen = false)}
    onsaved={(m) => {
      settingsOpen = false;
      onsettingssaved?.(m);
    }}
  />

  <SchedulerDialog
    open={schedulerOpen}
    {machine}
    schedule={effectiveSchedule}
    onclose={() => (schedulerOpen = false)}
    onschedulechange={handleScheduleChange}
  />
</div>

<style>
  .machine-panel {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* --- Header --- */
  .panel-header {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .header-row-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }

  .machine-name {
    font-size: 0.9rem;
    font-weight: 600;
    color: #e0e0e0;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .header-temps {
    display: flex;
    gap: 16px;
  }

  .btn-retry-header {
    background: transparent;
    border: 1px solid #ff9800;
    color: #ff9800;
    font-size: 0.9rem;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1;
  }

  .btn-retry-header:hover {
    background: rgba(255, 152, 0, 0.15);
    color: #ffb74d;
    border-color: #ffb74d;
  }

  .btn-settings {
    background: transparent;
    border: 1px solid transparent;
    color: #666;
    font-size: 0.9rem;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1;
  }

  .btn-settings:hover {
    color: #4fc3f7;
    border-color: #4fc3f7;
    background: rgba(79, 195, 247, 0.1);
  }

  .btn-remove {
    background: transparent;
    border: 1px solid transparent;
    color: #666;
    font-size: 0.9rem;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1;
  }

  .btn-remove:hover {
    color: #f44336;
    border-color: #f44336;
    background: rgba(244, 67, 54, 0.1);
  }

  /* --- Chart --- */
  .chart-section {
    position: relative;
  }

  .chart-section :global(.chart-container) {
    width: 100%;
  }

  .chart-toolbar {
    position: absolute;
    bottom: 8px;
    right: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    align-items: center;
  }

  .btn-chart-tool {
    background: rgba(13, 13, 26, 0.7);
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    color: #666;
    font-size: 0.85rem;
    cursor: pointer;
    padding: 2px 6px;
    line-height: 1;
  }

  .btn-chart-tool:hover {
    color: #ccc;
    border-color: #444;
  }

  /* --- Actions row --- */
  .actions-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  .btn-scheduler {
    background: transparent;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    color: #888;
    font-size: 0.75rem;
    padding: 5px 10px;
    cursor: pointer;
    margin-left: auto;
  }

  .btn-scheduler:hover {
    color: #4fc3f7;
    border-color: #4fc3f7;
    background: rgba(79, 195, 247, 0.05);
  }

  .btn-scheduler.active {
    color: #66bb6a;
    border-color: #66bb6a;
    background: rgba(102, 187, 106, 0.1);
  }

  .schedule-badge {
    font-size: 0.7rem;
    opacity: 0.7;
  }

  /* --- Controls --- */
  .controls-section {
    border-top: 1px solid #2a2a4a;
    padding-top: 4px;
  }

  .controls-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0 16px;
  }

  @media (max-width: 480px) {
    .header-temps {
      gap: 10px;
    }

    .header-actions {
      gap: 4px;
    }

    .btn-settings,
    .btn-remove,
    .btn-retry-header {
      padding: 6px 8px;
    }

    .actions-row {
      gap: 6px;
    }

    .controls-grid {
      grid-template-columns: 1fr;
      gap: 0;
    }
  }
</style>
