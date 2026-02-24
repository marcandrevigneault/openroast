<script lang="ts">
  import type { MachineState } from "$lib/stores/machine";
  import {
    addAlarm,
    removeAlarm,
    toggleAlarm,
    resetAlarms,
    createAlarmSet,
    formatAlarm,
    type AlarmSet,
    type AlarmStatus,
    type AlarmSensor,
    type AlarmDirection,
    type AlarmSound,
    type AlarmRepeat,
    type AlarmDef,
  } from "$lib/stores/alarms";
  import {
    playAlarmSound,
    stopAlarmSound,
    stopAllAlarmSounds,
  } from "$lib/utils/alarm-audio";

  interface Props {
    open: boolean;
    machine: MachineState;
    alarmSet: AlarmSet;
    onclose: () => void;
    onalarmsetchange: (set: AlarmSet) => void;
  }

  let { open, machine, alarmSet, onclose, onalarmsetchange }: Props = $props();

  // ── Local UI state ──────────────────────────
  let showAddForm = $state(false);
  let formSensorType = $state<string>("bt");
  let formDirection = $state<AlarmDirection>("rising");
  let formThreshold = $state(200);
  let formSound = $state<AlarmSound>("beep");
  let formRepeat = $state<AlarmRepeat>("once");

  // Derived stats
  let firedCount = $derived(
    alarmSet.alarms.filter((a: AlarmDef) => a.fired).length,
  );
  let enabledCount = $derived(
    alarmSet.alarms.filter((a: AlarmDef) => a.enabled).length,
  );

  // Sensor options for the dropdown
  let sensorOptions = $derived([
    { value: "et", label: "ET" },
    { value: "bt", label: "BT" },
    { value: "et_ror", label: "ET RoR" },
    { value: "bt_ror", label: "BT RoR" },
    ...machine.extraChannels.map((ch) => ({
      value: `extra:${ch.name}`,
      label: ch.name,
    })),
  ]);

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
  }

  function resetForm() {
    formSensorType = "bt";
    formDirection = "rising";
    formThreshold = 200;
    formSound = "beep";
    formRepeat = "once";
  }

  function buildSensor(): AlarmSensor {
    if (formSensorType.startsWith("extra:")) {
      return { type: "extra", channelName: formSensorType.slice(6) };
    }
    return { type: formSensorType as "et" | "bt" | "et_ror" | "bt_ror" };
  }

  function handleAddAlarm() {
    onalarmsetchange(
      addAlarm(alarmSet, {
        sensor: buildSensor(),
        threshold: formThreshold,
        direction: formDirection,
        sound: formSound,
        repeat: formRepeat,
        enabled: true,
      }),
    );
    showAddForm = false;
  }

  function handleRemoveAlarm(alarmId: string) {
    // Stop any active sound for this alarm
    const alarm = alarmSet.alarms.find((a: AlarmDef) => a.id === alarmId);
    if (alarm?.playbackId) {
      stopAlarmSound(alarm.playbackId);
    }
    onalarmsetchange(removeAlarm(alarmSet, alarmId));
  }

  function handleToggleAlarm(alarmId: string) {
    onalarmsetchange(toggleAlarm(alarmSet, alarmId));
  }

  function handleClearAll() {
    stopAllAlarmSounds();
    onalarmsetchange(createAlarmSet());
  }

  function handleArm() {
    onalarmsetchange({ ...resetAlarms(alarmSet), status: "armed" });
  }

  function handleDisarm() {
    // Stop all sounds
    for (const alarm of alarmSet.alarms) {
      if (alarm.playbackId) {
        stopAlarmSound(alarm.playbackId);
      }
    }
    onalarmsetchange({
      ...alarmSet,
      status: "idle",
      alarms: alarmSet.alarms.map((a: AlarmDef) => ({
        ...a,
        playbackId: null,
      })),
    });
  }

  function handleSilenceAll() {
    for (const alarm of alarmSet.alarms) {
      if (alarm.playbackId) {
        stopAlarmSound(alarm.playbackId);
      }
    }
    onalarmsetchange({
      ...alarmSet,
      alarms: alarmSet.alarms.map((a: AlarmDef) => ({
        ...a,
        playbackId: null,
      })),
    });
  }

  function handleReset() {
    stopAllAlarmSounds();
    onalarmsetchange(resetAlarms(alarmSet));
  }

  function handlePreviewSound() {
    playAlarmSound(formSound, "once");
  }

  function statusLabel(status: AlarmStatus): string {
    switch (status) {
      case "idle":
        return "Ready";
      case "armed":
        return "Armed";
      case "completed":
        return "Completed";
      default:
        return status;
    }
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_interactive_supports_focus -->
  <div
    class="overlay"
    role="dialog"
    aria-modal="true"
    onkeydown={handleKeydown}
  >
    <div class="dialog">
      <!-- Header -->
      <div class="dialog-header">
        <h2>Roast Alarms</h2>
        <button class="btn-close" onclick={onclose} aria-label="Close">✕</button
        >
      </div>

      <!-- Toolbar -->
      {#if alarmSet.alarms.length > 0 && alarmSet.status === "idle"}
        <div class="toolbar">
          <button class="btn-danger" onclick={handleClearAll}>Clear All</button>
        </div>
      {/if}

      <!-- Alarms list -->
      <div class="alarms-section">
        <div class="section-header">
          <h3>
            Alarms
            {#if alarmSet.alarms.length > 0}
              <span class="alarm-count">({firedCount}/{enabledCount})</span>
            {/if}
          </h3>
          {#if !showAddForm && alarmSet.status === "idle"}
            <button
              class="btn-add"
              onclick={() => {
                resetForm();
                showAddForm = true;
              }}>+ Add</button
            >
          {/if}
        </div>

        {#if alarmSet.alarms.length === 0 && !showAddForm}
          <p class="empty">
            No alarms configured. Add an alarm to get started.
          </p>
        {:else}
          <div class="alarm-list" role="list">
            {#each alarmSet.alarms as alarm, i (alarm.id)}
              <div
                class="alarm-item"
                class:fired={alarm.fired}
                class:disabled={!alarm.enabled}
                class:playing={alarm.playbackId !== null}
                role="listitem"
              >
                <label class="alarm-checkbox">
                  <input
                    type="checkbox"
                    checked={alarm.enabled}
                    onchange={() => handleToggleAlarm(alarm.id)}
                    disabled={alarmSet.status === "armed"}
                  />
                </label>
                <span class="alarm-number">{i + 1}.</span>
                <span class="alarm-trigger">{formatAlarm(alarm)}</span>
                <span class="alarm-meta">
                  {alarm.sound}
                  {#if alarm.repeat !== "once"}
                    &middot; {alarm.repeat}
                  {/if}
                </span>
                {#if alarm.fired}
                  <span class="alarm-check" title="Triggered">&#10003;</span>
                {/if}
                {#if alarm.playbackId}
                  <span class="alarm-playing" title="Playing">&#128266;</span>
                {/if}
                {#if alarmSet.status !== "armed"}
                  <button
                    class="btn-remove-alarm"
                    onclick={() => handleRemoveAlarm(alarm.id)}
                    title="Remove alarm"
                    aria-label="Remove alarm {i + 1}">✕</button
                  >
                {/if}
              </div>
            {/each}
          </div>
        {/if}

        <!-- Add alarm form -->
        {#if showAddForm}
          <div class="add-form">
            <h4 class="form-title">Add Alarm</h4>

            <!-- Sensor + Direction + Threshold -->
            <div class="form-group">
              <span class="form-group-label">When</span>
              <div class="form-fields">
                <select bind:value={formSensorType} class="input sensor-select">
                  {#each sensorOptions as opt (opt.value)}
                    <option value={opt.value}>{opt.label}</option>
                  {/each}
                </select>
                <select
                  bind:value={formDirection}
                  class="input direction-select"
                >
                  <option value="rising">Rising (&gt;=)</option>
                  <option value="falling">Falling (&lt;=)</option>
                  <option value="both">Both (&uarr;&darr;)</option>
                </select>
                <div class="inline-field">
                  <input
                    type="number"
                    class="input input-narrow"
                    bind:value={formThreshold}
                    step="0.1"
                    aria-label="Threshold"
                  />
                </div>
              </div>
            </div>

            <!-- Sound + Repeat -->
            <div class="form-group">
              <span class="form-group-label">Sound</span>
              <div class="form-fields">
                <select bind:value={formSound} class="input sound-select">
                  <option value="beep">Beep</option>
                  <option value="chime">Chime</option>
                  <option value="buzz">Buzz</option>
                  <option value="siren">Siren</option>
                </select>
                <button
                  class="btn-preview"
                  onclick={handlePreviewSound}
                  title="Preview sound"
                  type="button">&#128266;</button
                >
                <select bind:value={formRepeat} class="input repeat-select">
                  <option value="once">Once</option>
                  <option value="3x">3 times</option>
                </select>
              </div>
            </div>

            <div class="form-buttons">
              <button
                class="btn-secondary btn-small"
                onclick={() => (showAddForm = false)}>Cancel</button
              >
              <button class="btn-primary btn-small" onclick={handleAddAlarm}
                >Add Alarm</button
              >
            </div>
          </div>
        {/if}
      </div>

      <!-- Footer -->
      <div class="dialog-footer">
        <span class="status-label">{statusLabel(alarmSet.status)}</span>
        <div class="footer-buttons">
          <button class="btn-secondary" onclick={onclose}>Close</button>
          {#if alarmSet.status === "idle" && alarmSet.alarms.length > 0}
            <button class="btn-primary" onclick={handleArm}>Arm Alarms</button>
          {:else if alarmSet.status === "armed"}
            <button class="btn-secondary" onclick={handleSilenceAll}
              >Silence All</button
            >
            <button class="btn-danger" onclick={handleDisarm}>Disarm</button>
          {:else if alarmSet.status === "completed"}
            <button class="btn-secondary" onclick={handleReset}>Reset</button>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .dialog {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 10px;
    padding: 20px;
    width: 520px;
    max-width: 95vw;
    max-height: 85vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .dialog-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .dialog-header h2 {
    font-size: 1rem;
    color: #e0e0e0;
    margin: 0;
    flex: 1;
  }

  .btn-close {
    background: transparent;
    border: none;
    color: #666;
    font-size: 1rem;
    cursor: pointer;
    padding: 2px 6px;
  }

  .btn-close:hover {
    color: #f44336;
  }

  /* ── Toolbar ── */
  .toolbar {
    display: flex;
    gap: 8px;
  }

  /* ── Alarms section ── */
  .alarms-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .section-header h3 {
    font-size: 0.75rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0;
  }

  .alarm-count {
    color: #666;
    font-weight: 400;
  }

  .alarm-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 240px;
    overflow-y: auto;
  }

  .alarm-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    font-size: 0.8rem;
    color: #e0e0e0;
  }

  .alarm-item.fired {
    opacity: 0.5;
  }

  .alarm-item.disabled {
    opacity: 0.35;
  }

  .alarm-item.playing {
    border-color: #ff9800;
    background: rgba(255, 152, 0, 0.05);
  }

  .alarm-checkbox input {
    margin: 0;
    cursor: pointer;
  }

  .alarm-number {
    color: #666;
    min-width: 18px;
  }

  .alarm-trigger {
    color: #4fc3f7;
    white-space: nowrap;
  }

  .alarm-meta {
    flex: 1;
    color: #666;
    font-size: 0.7rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .alarm-check {
    color: #ff9800;
    font-size: 0.9rem;
  }

  .alarm-playing {
    font-size: 0.8rem;
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.4;
    }
  }

  .btn-remove-alarm {
    background: transparent;
    border: none;
    color: #666;
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0 4px;
    flex-shrink: 0;
  }

  .btn-remove-alarm:hover {
    color: #f44336;
  }

  .empty {
    color: #555;
    font-size: 0.8rem;
    text-align: center;
    padding: 16px;
    margin: 0;
  }

  /* ── Add form ── */
  .add-form {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .form-title {
    font-size: 0.8rem;
    color: #e0e0e0;
    margin: 0;
    font-weight: 500;
  }

  .form-group {
    display: flex;
    gap: 10px;
    align-items: baseline;
  }

  .form-group-label {
    font-size: 0.7rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    min-width: 42px;
    flex-shrink: 0;
    padding-top: 6px;
  }

  .form-fields {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
    flex: 1;
  }

  .inline-field {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .input {
    background: #0d0d1a;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    padding: 5px 8px;
    color: #e0e0e0;
    font-size: 0.8rem;
  }

  .input:focus {
    outline: none;
    border-color: #4fc3f7;
  }

  .input-narrow {
    width: 72px;
  }

  .sensor-select {
    width: 90px;
  }

  .direction-select {
    width: 110px;
  }

  .sound-select {
    width: 90px;
  }

  .repeat-select {
    width: 110px;
  }

  .btn-preview {
    background: transparent;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    color: #888;
    font-size: 0.85rem;
    cursor: pointer;
    padding: 3px 8px;
    line-height: 1;
  }

  .btn-preview:hover {
    color: #4fc3f7;
    border-color: #4fc3f7;
  }

  .form-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
    padding-top: 2px;
    border-top: 1px solid #2a2a4a;
  }

  /* ── Footer ── */
  .dialog-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #2a2a4a;
    padding-top: 12px;
  }

  .status-label {
    font-size: 0.75rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .footer-buttons {
    display: flex;
    gap: 6px;
  }

  /* ── Shared buttons ── */
  .btn-primary {
    background: #2e7d32;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
  }

  .btn-primary:hover {
    background: #388e3c;
  }

  .btn-primary:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .btn-secondary {
    background: #2a2a4a;
    color: #ccc;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .btn-secondary:hover {
    background: #3a3a5a;
  }

  .btn-danger {
    background: transparent;
    color: #f44336;
    border: 1px solid #f44336;
    border-radius: 6px;
    padding: 7px 15px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .btn-danger:hover {
    background: rgba(244, 67, 54, 0.1);
  }

  .btn-add {
    background: transparent;
    color: #4fc3f7;
    border: 1px solid #4fc3f7;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.75rem;
    cursor: pointer;
  }

  .btn-add:hover {
    background: rgba(79, 195, 247, 0.1);
  }

  .btn-small {
    padding: 5px 10px;
    font-size: 0.75rem;
  }

  @media (max-width: 480px) {
    .dialog {
      width: 95vw;
      max-height: 90vh;
      padding: 14px;
    }

    .toolbar {
      flex-wrap: wrap;
      gap: 6px;
    }

    .alarm-list {
      max-height: 200px;
    }

    .alarm-item {
      font-size: 0.75rem;
      gap: 4px;
      padding: 8px 6px;
    }

    .form-group {
      flex-direction: column;
      gap: 6px;
    }

    .form-group-label {
      min-width: 0;
      padding-top: 0;
    }

    .form-fields {
      gap: 6px;
    }

    .input-narrow {
      width: 64px;
    }

    .sensor-select,
    .direction-select,
    .sound-select,
    .repeat-select {
      width: auto;
      flex: 1;
    }

    .dialog-footer {
      flex-direction: column;
      gap: 8px;
      align-items: stretch;
    }

    .footer-buttons {
      justify-content: stretch;
    }

    .footer-buttons .btn-primary,
    .footer-buttons .btn-secondary,
    .footer-buttons .btn-danger {
      flex: 1;
      text-align: center;
    }

    .btn-primary,
    .btn-secondary,
    .btn-danger {
      padding: 10px 14px;
    }
  }
</style>
