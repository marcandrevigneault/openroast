<script lang="ts">
  import type { MachineState, ControlConfig } from "$lib/stores/machine";
  import {
    addStep,
    removeStep,
    toggleStep,
    resetSchedule,
    importFromProfile,
    formatTrigger,
    sortSteps,
    createSchedule,
    type RoastSchedule,
    type ScheduleTrigger,
    type ControlAction,
    type SchedulerStatus,
  } from "$lib/stores/scheduler";
  import {
    listProfiles,
    getProfile,
    listSchedules,
    getSchedule,
    saveSchedule,
    deleteSchedule,
    type ProfileSummary,
    type ScheduleSummary,
  } from "$lib/utils/api";

  interface Props {
    open: boolean;
    machine: MachineState;
    schedule: RoastSchedule;
    onclose: () => void;
    onschedulechange: (schedule: RoastSchedule) => void;
  }

  let { open, machine, schedule, onclose, onschedulechange }: Props = $props();

  // ── Local UI state ──────────────────────────
  type View = "main" | "import" | "load" | "save";
  let view = $state<View>("main");
  let profiles = $state<ProfileSummary[]>([]);
  let loadingProfiles = $state(false);
  let importError = $state<string | null>(null);

  // Save/Load state
  let savedSchedules = $state<ScheduleSummary[]>([]);
  let loadingSchedules = $state(false);
  let scheduleError = $state<string | null>(null);
  let saveName = $state("");

  // Add step form
  let showAddForm = $state(false);
  let triggerType = $state<"time" | "bt_threshold" | "et_threshold">("time");
  let triggerMinutes = $state(0);
  let triggerSeconds = $state(0);
  let triggerTemp = $state(150);
  let triggerDirection = $state<"rising" | "falling">("rising");
  let formActions = $state<{ channel: string; value: number }[]>([]);

  let availableControls = $derived(machine.controls);

  function resetForm() {
    triggerType = "time";
    triggerMinutes = 0;
    triggerSeconds = 0;
    triggerTemp = 150;
    triggerDirection = "rising";
    formActions = [];
    if (availableControls.length > 0) {
      formActions = [
        {
          channel: availableControls[0].channel,
          value: availableControls[0].min,
        },
      ];
    }
  }

  // Derived schedule stats
  let firedCount = $derived(schedule.steps.filter((s) => s.fired).length);
  let enabledCount = $derived(schedule.steps.filter((s) => s.enabled).length);

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
  }

  // ── Import flow ─────────────────────────────
  async function openImport() {
    view = "import";
    loadingProfiles = true;
    importError = null;
    try {
      profiles = await listProfiles();
    } catch {
      importError = "Failed to load profiles";
    } finally {
      loadingProfiles = false;
    }
  }

  async function handleImportProfile(profileId: string) {
    loadingProfiles = true;
    importError = null;
    try {
      const profile = await getProfile(profileId);
      const steps = importFromProfile(profile.controls, machine.controls);
      if (steps.length === 0) {
        importError = "No control data in this profile";
        loadingProfiles = false;
        return;
      }
      const newSchedule: RoastSchedule = {
        steps: sortSteps(steps),
        status: "idle",
        sourceProfileName: profile.name,
      };
      onschedulechange(newSchedule);
      view = "main";
    } catch {
      importError = "Failed to load profile";
    } finally {
      loadingProfiles = false;
    }
  }

  // ── Save/Load flow ─────────────────────────
  function openSave() {
    saveName = schedule.sourceProfileName
      ? `${schedule.sourceProfileName} schedule`
      : "";
    scheduleError = null;
    view = "save";
  }

  async function handleSaveSchedule() {
    if (!saveName.trim()) return;
    scheduleError = null;
    try {
      await saveSchedule({
        name: saveName.trim(),
        machine_name: machine.machineName,
        steps: schedule.steps.map((s) => ({
          id: s.id,
          trigger: s.trigger,
          actions: s.actions,
          fired: false,
          enabled: s.enabled,
        })),
        source_profile_name: schedule.sourceProfileName,
      });
      view = "main";
    } catch {
      scheduleError = "Failed to save schedule";
    }
  }

  async function openLoad() {
    view = "load";
    loadingSchedules = true;
    scheduleError = null;
    try {
      savedSchedules = await listSchedules();
    } catch {
      scheduleError = "Failed to load schedules";
    } finally {
      loadingSchedules = false;
    }
  }

  async function handleLoadSchedule(id: string) {
    loadingSchedules = true;
    scheduleError = null;
    try {
      const data = await getSchedule(id);
      const newSchedule: RoastSchedule = {
        steps: data.steps.map((s) => ({
          id: s.id,
          trigger: s.trigger as unknown as ScheduleTrigger,
          actions: s.actions,
          fired: false,
          enabled: s.enabled,
        })),
        status: "idle",
        sourceProfileName: data.source_profile_name,
      };
      onschedulechange(newSchedule);
      view = "main";
    } catch {
      scheduleError = "Failed to load schedule";
    } finally {
      loadingSchedules = false;
    }
  }

  async function handleDeleteSchedule(id: string) {
    try {
      await deleteSchedule(id);
      savedSchedules = savedSchedules.filter((s) => s.id !== id);
    } catch {
      scheduleError = "Failed to delete schedule";
    }
  }

  // ── Step management ─────────────────────────
  function handleAddStep() {
    let trigger: ScheduleTrigger;
    if (triggerType === "time") {
      trigger = {
        type: "time",
        timestamp_ms: (triggerMinutes * 60 + triggerSeconds) * 1000,
      };
    } else {
      trigger = {
        type: triggerType,
        temperature: triggerTemp,
        direction: triggerDirection,
      };
    }
    const actions: ControlAction[] = formActions.map((a) => ({
      channel: a.channel,
      value: a.value,
    }));
    if (actions.length === 0) return;

    onschedulechange(addStep(schedule, { trigger, actions, enabled: true }));
    showAddForm = false;
  }

  function handleRemoveStep(stepId: string) {
    onschedulechange(removeStep(schedule, stepId));
  }

  function handleToggleStep(stepId: string) {
    onschedulechange(toggleStep(schedule, stepId));
  }

  function handleClearAll() {
    onschedulechange(createSchedule());
  }

  // ── Schedule control ────────────────────────
  function handleStart() {
    onschedulechange({ ...resetSchedule(schedule), status: "running" });
  }

  function handlePause() {
    onschedulechange({ ...schedule, status: "paused" });
  }

  function handleResume() {
    onschedulechange({ ...schedule, status: "running" });
  }

  function handleStop() {
    onschedulechange(resetSchedule(schedule));
  }

  // ── Helpers ─────────────────────────────────
  function findControl(channel: string): ControlConfig | undefined {
    return machine.controls.find((c) => c.channel === channel);
  }

  function formatActions(actions: ControlAction[]): string {
    return actions
      .map((a) => {
        const ctrl = findControl(a.channel);
        const name = ctrl?.name ?? a.channel;
        const unit = ctrl?.unit ?? "";
        return `${name}: ${a.value}${unit}`;
      })
      .join(", ");
  }

  function addFormAction() {
    if (availableControls.length === 0) return;
    formActions = [
      ...formActions,
      {
        channel: availableControls[0].channel,
        value: availableControls[0].min,
      },
    ];
  }

  function removeFormAction(index: number) {
    formActions = formActions.filter((_, i) => i !== index);
  }

  function updateFormActionChannel(index: number, channel: string) {
    const ctrl = findControl(channel);
    formActions = formActions.map((a, i) =>
      i === index ? { channel, value: ctrl?.min ?? 0 } : a,
    );
  }

  function updateFormActionValue(index: number, value: number) {
    formActions = formActions.map((a, i) =>
      i === index ? { ...a, value } : a,
    );
  }

  function statusLabel(status: SchedulerStatus): string {
    switch (status) {
      case "idle":
        return "Ready";
      case "running":
        return "Running";
      case "paused":
        return "Paused";
      case "completed":
        return "Completed";
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
        <h2>Roast Schedule</h2>
        {#if schedule.sourceProfileName}
          <span class="source-label">from: {schedule.sourceProfileName}</span>
        {/if}
        <button class="btn-close" onclick={onclose} aria-label="Close">✕</button
        >
      </div>

      {#if view === "import"}
        <!-- Import view -->
        <div class="import-section">
          <div class="section-header">
            <h3>Select Profile</h3>
            <button class="btn-back" onclick={() => (view = "main")}
              >&larr; Back</button
            >
          </div>
          {#if loadingProfiles}
            <p class="loading">Loading profiles...</p>
          {:else if importError}
            <p class="error">{importError}</p>
          {:else if profiles.length === 0}
            <p class="empty">No saved profiles found.</p>
          {:else}
            <div class="profile-list">
              {#each profiles as p (p.id)}
                <button
                  class="profile-item"
                  onclick={() => handleImportProfile(p.id)}
                >
                  <span class="profile-name">{p.name}</span>
                  <span class="profile-meta"
                    >{p.machine || "Unknown machine"} &middot; {p.data_points} points</span
                  >
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {:else if view === "load"}
        <!-- Load view -->
        <div class="import-section">
          <div class="section-header">
            <h3>Load Schedule</h3>
            <button class="btn-back" onclick={() => (view = "main")}
              >&larr; Back</button
            >
          </div>
          {#if loadingSchedules}
            <p class="loading">Loading schedules...</p>
          {:else if scheduleError}
            <p class="error">{scheduleError}</p>
          {:else if savedSchedules.length === 0}
            <p class="empty">No saved schedules found.</p>
          {:else}
            <div class="profile-list">
              {#each savedSchedules as s (s.id)}
                <div class="schedule-list-item">
                  <button
                    class="profile-item schedule-item-btn"
                    onclick={() => handleLoadSchedule(s.id)}
                  >
                    <span class="profile-name">{s.name}</span>
                    <span class="profile-meta"
                      >{s.machine_name || "Unknown machine"} &middot; {s.step_count}
                      steps</span
                    >
                  </button>
                  <button
                    class="btn-delete-schedule"
                    onclick={() => handleDeleteSchedule(s.id)}
                    title="Delete schedule">✕</button
                  >
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {:else if view === "save"}
        <!-- Save view -->
        <div class="import-section">
          <div class="section-header">
            <h3>Save Schedule</h3>
            <button class="btn-back" onclick={() => (view = "main")}
              >&larr; Back</button
            >
          </div>
          {#if scheduleError}
            <p class="error">{scheduleError}</p>
          {/if}
          <div class="save-form">
            <input
              type="text"
              class="input save-name-input"
              placeholder="Schedule name"
              bind:value={saveName}
              aria-label="Schedule name"
              onkeydown={(e) => {
                if (e.key === "Enter") handleSaveSchedule();
              }}
            />
            <button
              class="btn-primary"
              onclick={handleSaveSchedule}
              disabled={!saveName.trim()}
            >
              Save
            </button>
          </div>
        </div>
      {:else}
        <!-- Main view -->
        <div class="toolbar">
          <button class="btn-secondary" onclick={openImport}
            >Import from Profile</button
          >
          <button class="btn-secondary" onclick={openLoad}>Load</button>
          {#if schedule.steps.length > 0}
            <button class="btn-secondary" onclick={openSave}>Save</button>
            <button class="btn-danger" onclick={handleClearAll}
              >Clear All</button
            >
          {/if}
        </div>

        <!-- Steps list -->
        <div class="steps-section">
          <div class="section-header">
            <h3>
              Steps
              {#if schedule.steps.length > 0}
                <span class="step-count">({firedCount}/{enabledCount})</span>
              {/if}
            </h3>
            {#if !showAddForm}
              <button
                class="btn-add"
                onclick={() => {
                  resetForm();
                  showAddForm = true;
                }}>+ Add</button
              >
            {/if}
          </div>

          {#if schedule.steps.length === 0}
            <p class="empty">
              No steps yet. Add steps manually or import from a saved profile.
            </p>
          {:else}
            <div class="step-list" role="list">
              {#each schedule.steps as step, i (step.id)}
                <div
                  class="step-item"
                  class:fired={step.fired}
                  class:disabled={!step.enabled}
                  role="listitem"
                >
                  <label class="step-checkbox">
                    <input
                      type="checkbox"
                      checked={step.enabled}
                      onchange={() => handleToggleStep(step.id)}
                      disabled={schedule.status === "running"}
                    />
                  </label>
                  <span class="step-number">{i + 1}.</span>
                  <span class="step-trigger">{formatTrigger(step.trigger)}</span
                  >
                  <span class="step-arrow">&rarr;</span>
                  <span class="step-actions">{formatActions(step.actions)}</span
                  >
                  {#if step.fired}
                    <span class="step-check" title="Fired">&#10003;</span>
                  {/if}
                  {#if schedule.status !== "running"}
                    <button
                      class="btn-remove-step"
                      onclick={() => handleRemoveStep(step.id)}
                      title="Remove step"
                      aria-label="Remove step {i + 1}">✕</button
                    >
                  {/if}
                </div>
              {/each}
            </div>
          {/if}

          <!-- Add step form -->
          {#if showAddForm}
            <div class="add-form">
              <h4 class="form-title">Add Step</h4>

              <!-- Trigger -->
              <div class="form-group">
                <span class="form-group-label">When</span>
                <div class="form-fields">
                  <select bind:value={triggerType} class="input trigger-select">
                    <option value="time">Time</option>
                    <option value="bt_threshold">BT Threshold</option>
                    <option value="et_threshold">ET Threshold</option>
                  </select>
                  {#if triggerType === "time"}
                    <div class="inline-field">
                      <input
                        type="number"
                        class="input input-narrow"
                        bind:value={triggerMinutes}
                        min="0"
                        max="59"
                        aria-label="Minutes"
                      />
                      <span class="field-hint">min</span>
                    </div>
                    <div class="inline-field">
                      <input
                        type="number"
                        class="input input-narrow"
                        bind:value={triggerSeconds}
                        min="0"
                        max="59"
                        aria-label="Seconds"
                      />
                      <span class="field-hint">sec</span>
                    </div>
                  {:else}
                    <select
                      bind:value={triggerDirection}
                      class="input direction-select"
                    >
                      <option value="rising">Rising (&gt;=)</option>
                      <option value="falling">Falling (&lt;=)</option>
                    </select>
                    <div class="inline-field">
                      <input
                        type="number"
                        class="input input-narrow"
                        bind:value={triggerTemp}
                        min="0"
                        max="500"
                        aria-label="Temperature"
                      />
                      <span class="field-hint">&deg;C</span>
                    </div>
                  {/if}
                </div>
              </div>

              <!-- Actions -->
              <div class="form-group">
                <span class="form-group-label">Set</span>
                <div class="actions-list">
                  {#each formActions as action, i (i)}
                    <div class="action-row">
                      <select
                        value={action.channel}
                        class="input channel-select"
                        aria-label="Channel"
                        onchange={(e) =>
                          updateFormActionChannel(
                            i,
                            (e.target as HTMLSelectElement).value,
                          )}
                      >
                        {#each availableControls as ctrl (ctrl.channel)}
                          <option value={ctrl.channel}>{ctrl.name}</option>
                        {/each}
                      </select>
                      <span class="action-to">to</span>
                      <input
                        type="number"
                        class="input input-narrow"
                        value={action.value}
                        min={findControl(action.channel)?.min ?? 0}
                        max={findControl(action.channel)?.max ?? 100}
                        step={findControl(action.channel)?.step ?? 1}
                        aria-label="Value"
                        oninput={(e) =>
                          updateFormActionValue(
                            i,
                            parseFloat((e.target as HTMLInputElement).value),
                          )}
                      />
                      <span class="field-hint"
                        >{findControl(action.channel)?.unit ?? ""}</span
                      >
                      {#if formActions.length > 1}
                        <button
                          class="btn-remove-action"
                          onclick={() => removeFormAction(i)}
                          title="Remove action">✕</button
                        >
                      {/if}
                    </div>
                  {/each}
                  <button class="btn-add-action" onclick={addFormAction}
                    >+ Action</button
                  >
                </div>
              </div>

              <div class="form-buttons">
                <button
                  class="btn-secondary btn-small"
                  onclick={() => (showAddForm = false)}>Cancel</button
                >
                <button
                  class="btn-primary btn-small"
                  onclick={handleAddStep}
                  disabled={formActions.length === 0}>Add Step</button
                >
              </div>
            </div>
          {/if}
        </div>

        <!-- Footer with schedule controls -->
        <div class="dialog-footer">
          <span class="status-label">{statusLabel(schedule.status)}</span>
          <div class="footer-buttons">
            <button class="btn-secondary" onclick={onclose}>Close</button>
            {#if schedule.status === "idle" && schedule.steps.length > 0}
              <button class="btn-primary" onclick={handleStart}
                >Start Schedule</button
              >
            {:else if schedule.status === "running"}
              <button class="btn-secondary" onclick={handlePause}>Pause</button>
              <button class="btn-danger" onclick={handleStop}>Stop</button>
            {:else if schedule.status === "paused"}
              <button class="btn-primary" onclick={handleResume}>Resume</button>
              <button class="btn-danger" onclick={handleStop}>Stop</button>
            {:else if schedule.status === "completed"}
              <button class="btn-secondary" onclick={handleStop}>Reset</button>
            {/if}
          </div>
        </div>
      {/if}
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

  .source-label {
    font-size: 0.7rem;
    color: #666;
    font-style: italic;
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

  /* ── Steps ── */
  .steps-section {
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

  .step-count {
    color: #666;
    font-weight: 400;
  }

  .step-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 240px;
    overflow-y: auto;
  }

  .step-item {
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

  .step-item.fired {
    opacity: 0.5;
  }

  .step-item.disabled {
    opacity: 0.35;
  }

  .step-checkbox input {
    margin: 0;
    cursor: pointer;
  }

  .step-number {
    color: #666;
    min-width: 18px;
  }

  .step-trigger {
    color: #4fc3f7;
    white-space: nowrap;
  }

  .step-arrow {
    color: #444;
  }

  .step-actions {
    flex: 1;
    color: #ccc;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-check {
    color: #66bb6a;
    font-size: 0.9rem;
  }

  .btn-remove-step {
    background: transparent;
    border: none;
    color: #666;
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0 4px;
    flex-shrink: 0;
  }

  .btn-remove-step:hover {
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
    min-width: 32px;
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

  .field-hint {
    font-size: 0.7rem;
    color: #666;
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
    width: 56px;
  }

  .trigger-select {
    width: 120px;
  }

  .direction-select {
    width: 110px;
  }

  .channel-select {
    width: 100px;
  }

  .actions-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
  }

  .action-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .action-to {
    font-size: 0.7rem;
    color: #555;
  }

  .btn-remove-action {
    background: transparent;
    border: none;
    color: #555;
    cursor: pointer;
    padding: 0 2px;
    font-size: 0.8rem;
    line-height: 1;
  }

  .btn-remove-action:hover {
    color: #f44336;
  }

  .btn-add-action {
    background: transparent;
    border: none;
    color: #4fc3f7;
    font-size: 0.7rem;
    cursor: pointer;
    padding: 0;
    text-align: left;
    width: fit-content;
  }

  .btn-add-action:hover {
    text-decoration: underline;
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

  /* ── Import ── */
  .import-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .btn-back {
    background: transparent;
    border: none;
    color: #4fc3f7;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .profile-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 300px;
    overflow-y: auto;
  }

  .profile-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px 12px;
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    cursor: pointer;
    text-align: left;
    color: #e0e0e0;
  }

  .profile-item:hover {
    border-color: #4fc3f7;
    background: rgba(79, 195, 247, 0.05);
  }

  .profile-name {
    font-size: 0.85rem;
    font-weight: 500;
  }

  .profile-meta {
    font-size: 0.7rem;
    color: #666;
  }

  .schedule-list-item {
    display: flex;
    gap: 4px;
    align-items: stretch;
  }

  .schedule-item-btn {
    flex: 1;
  }

  .btn-delete-schedule {
    background: transparent;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    color: #555;
    cursor: pointer;
    padding: 0 8px;
    font-size: 0.8rem;
    flex-shrink: 0;
  }

  .btn-delete-schedule:hover {
    color: #f44336;
    border-color: #f44336;
  }

  .save-form {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .save-name-input {
    flex: 1;
  }

  .loading,
  .error {
    font-size: 0.8rem;
    text-align: center;
    padding: 16px;
    margin: 0;
  }

  .loading {
    color: #888;
  }

  .error {
    color: #f44336;
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
</style>
