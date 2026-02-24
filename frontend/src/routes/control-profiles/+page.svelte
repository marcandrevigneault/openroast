<script lang="ts">
  import { onMount } from "svelte";
  import {
    listSchedules,
    getSchedule,
    updateSchedule,
    deleteSchedule,
    type ScheduleSummary,
    type SavedScheduleData,
  } from "$lib/utils/api";
  import { addToast } from "$lib/stores/toast";
  import ToastContainer from "$lib/components/ToastContainer.svelte";

  let schedules = $state<ScheduleSummary[]>([]);
  let loading = $state(true);
  let selected = $state<SavedScheduleData | null>(null);
  let loadingDetail = $state(false);
  let editing = $state(false);
  let editName = $state("");
  let editSteps = $state<SavedScheduleData["steps"]>([]);
  let saving = $state(false);
  let confirmDeleteId = $state<string | null>(null);

  async function load() {
    loading = true;
    try {
      schedules = await listSchedules();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load";
      addToast(msg, "error");
    } finally {
      loading = false;
    }
  }

  async function viewSchedule(id: string) {
    loadingDetail = true;
    try {
      selected = await getSchedule(id);
      editing = false;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load";
      addToast(msg, "error");
    } finally {
      loadingDetail = false;
    }
  }

  function startEdit() {
    if (!selected) return;
    editName = selected.name;
    editSteps = selected.steps.map((s) => ({ ...s }));
    editing = true;
  }

  function cancelEdit() {
    editing = false;
  }

  async function saveEdit() {
    if (!selected) return;
    saving = true;
    try {
      const updated = await updateSchedule(selected.id, {
        name: editName,
        machine_name: selected.machine_name,
        steps: editSteps,
        source_profile_name: selected.source_profile_name,
      });
      selected = updated;
      editing = false;
      // Update the list
      schedules = schedules.map((s) =>
        s.id === updated.id
          ? { ...s, name: updated.name, step_count: updated.steps.length }
          : s,
      );
      addToast("Control profile saved", "info");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to save";
      addToast(msg, "error");
    } finally {
      saving = false;
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteSchedule(id);
      schedules = schedules.filter((s) => s.id !== id);
      if (selected?.id === id) selected = null;
      confirmDeleteId = null;
      addToast("Control profile deleted", "info");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to delete";
      addToast(msg, "error");
    }
  }

  function removeStep(index: number) {
    editSteps = editSteps.filter((_, i) => i !== index);
  }

  function addNewStep() {
    editSteps = [
      ...editSteps,
      {
        id: `new-${Date.now()}`,
        trigger: { type: "time", timestamp_ms: 0 },
        actions: [{ channel: "", value: 0 }],
        enabled: true,
      },
    ];
  }

  function updateTriggerType(index: number, type: string) {
    editSteps = editSteps.map((s, i) => {
      if (i !== index) return s;
      if (type === "time") {
        return { ...s, trigger: { type: "time", timestamp_ms: 0 } };
      }
      return {
        ...s,
        trigger: {
          type,
          temperature: 150,
          direction: "rising",
        },
      };
    });
  }

  function updateTriggerField(index: number, field: string, value: unknown) {
    editSteps = editSteps.map((s, i) =>
      i === index ? { ...s, trigger: { ...s.trigger, [field]: value } } : s,
    );
  }

  function updateActionChannel(
    stepIndex: number,
    actionIndex: number,
    channel: string,
  ) {
    editSteps = editSteps.map((s, i) => {
      if (i !== stepIndex) return s;
      return {
        ...s,
        actions: s.actions.map((a, j) =>
          j === actionIndex ? { ...a, channel } : a,
        ),
      };
    });
  }

  function updateActionValue(
    stepIndex: number,
    actionIndex: number,
    value: number,
  ) {
    editSteps = editSteps.map((s, i) => {
      if (i !== stepIndex) return s;
      return {
        ...s,
        actions: s.actions.map((a, j) =>
          j === actionIndex ? { ...a, value } : a,
        ),
      };
    });
  }

  function addAction(stepIndex: number) {
    editSteps = editSteps.map((s, i) => {
      if (i !== stepIndex) return s;
      return { ...s, actions: [...s.actions, { channel: "", value: 0 }] };
    });
  }

  function removeAction(stepIndex: number, actionIndex: number) {
    editSteps = editSteps.map((s, i) => {
      if (i !== stepIndex) return s;
      return {
        ...s,
        actions: s.actions.filter((_, j) => j !== actionIndex),
      };
    });
  }

  function toggleStepEnabled(index: number) {
    editSteps = editSteps.map((s, i) =>
      i === index ? { ...s, enabled: !s.enabled } : s,
    );
  }

  function getTriggerMinutes(trigger: Record<string, unknown>): number {
    const ms = (trigger.timestamp_ms as number) ?? 0;
    return Math.floor(ms / 60000);
  }

  function getTriggerSeconds(trigger: Record<string, unknown>): number {
    const ms = (trigger.timestamp_ms as number) ?? 0;
    return Math.floor((ms % 60000) / 1000);
  }

  function formatTrigger(trigger: Record<string, unknown>): string {
    const type = trigger.type as string;
    if (type === "time") {
      const ms = trigger.timestamp_ms as number;
      const s = Math.floor(ms / 1000);
      const m = Math.floor(s / 60);
      return `Time ${m}:${String(s % 60).padStart(2, "0")}`;
    }
    if (type === "bt_threshold" || type === "et_threshold") {
      const label = type === "bt_threshold" ? "BT" : "ET";
      const dir = trigger.direction as string;
      return `${label} ${dir} ${trigger.temperature}°`;
    }
    return JSON.stringify(trigger);
  }

  function formatActions(
    actions: { channel: string; value: number }[],
  ): string {
    return actions.map((a) => `${a.channel}=${a.value}`).join(", ");
  }

  function formatDate(iso: string): string {
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  onMount(load);
</script>

<ToastContainer />

<div class="cp-page">
  <h2 class="page-title">Control Profiles</h2>
  <p class="page-desc">
    Reusable control recipes — define steps to automate your roast.
  </p>

  {#if loading}
    <p class="loading">Loading control profiles...</p>
  {:else if schedules.length === 0}
    <div class="empty-state">
      <p>No control profiles yet.</p>
      <p class="hint">
        Create a schedule during a roast session, or import from a saved
        profile.
      </p>
    </div>
  {:else}
    <div class="schedule-list">
      {#each schedules as s (s.id)}
        <div class="schedule-card" class:selected={selected?.id === s.id}>
          <button class="card-body" onclick={() => viewSchedule(s.id)}>
            <div class="card-title">{s.name}</div>
            <div class="card-meta">
              {#if s.machine_name}
                <span>{s.machine_name}</span>
                <span class="sep">·</span>
              {/if}
              <span>{formatDate(s.created_at)}</span>
              <span class="sep">·</span>
              <span>{s.step_count} steps</span>
            </div>
          </button>
          <div class="card-actions">
            {#if confirmDeleteId === s.id}
              <button
                class="btn-confirm-delete"
                onclick={() => handleDelete(s.id)}>Confirm</button
              >
              <button
                class="btn-cancel-delete"
                onclick={() => (confirmDeleteId = null)}>Cancel</button
              >
            {:else}
              <button
                class="btn-delete"
                onclick={() => (confirmDeleteId = s.id)}
                title="Delete">&#128465;</button
              >
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if selected}
    <div class="detail-panel">
      <div class="detail-header">
        {#if editing}
          <input class="edit-name" type="text" bind:value={editName} />
        {:else}
          <h3>{selected.name}</h3>
        {/if}
        <div class="detail-actions">
          {#if editing}
            <button class="btn-save" onclick={saveEdit} disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
            <button class="btn-cancel" onclick={cancelEdit}>Cancel</button>
          {:else}
            <button class="btn-edit" onclick={startEdit}>Edit</button>
          {/if}
          <button class="btn-close" onclick={() => (selected = null)}
            >&times;</button
          >
        </div>
      </div>

      <div class="detail-meta">
        {#if selected.machine_name}
          <span><strong>Machine:</strong> {selected.machine_name}</span>
        {/if}
        <span><strong>Date:</strong> {formatDate(selected.created_at)}</span>
        {#if selected.source_profile_name}
          <span><strong>Source:</strong> {selected.source_profile_name}</span>
        {/if}
      </div>

      <div class="steps-section">
        <h4>Steps ({editing ? editSteps.length : selected.steps.length})</h4>
        <div class="steps-list">
          {#if editing}
            {#each editSteps as step, i (step.id)}
              <div class="step-edit-card">
                <div class="step-edit-header">
                  <span class="step-num">{i + 1}</span>
                  <button
                    class="btn-toggle-enabled"
                    class:off={!step.enabled}
                    onclick={() => toggleStepEnabled(i)}
                  >
                    {step.enabled ? "On" : "Off"}
                  </button>
                  <button class="btn-remove-step" onclick={() => removeStep(i)}
                    >&times;</button
                  >
                </div>
                <div class="step-edit-trigger">
                  <label class="edit-label">Trigger</label>
                  <select
                    class="edit-select"
                    value={step.trigger.type}
                    onchange={(e) =>
                      updateTriggerType(
                        i,
                        (e.target as HTMLSelectElement).value,
                      )}
                  >
                    <option value="time">Time</option>
                    <option value="bt_threshold">BT Threshold</option>
                    <option value="et_threshold">ET Threshold</option>
                  </select>
                  {#if step.trigger.type === "time"}
                    <input
                      class="edit-input-sm"
                      type="number"
                      min="0"
                      value={getTriggerMinutes(step.trigger)}
                      onchange={(e) =>
                        updateTriggerField(
                          i,
                          "timestamp_ms",
                          Number((e.target as HTMLInputElement).value) * 60000 +
                            getTriggerSeconds(step.trigger) * 1000,
                        )}
                    />
                    <span class="edit-unit">m</span>
                    <input
                      class="edit-input-sm"
                      type="number"
                      min="0"
                      max="59"
                      value={getTriggerSeconds(step.trigger)}
                      onchange={(e) =>
                        updateTriggerField(
                          i,
                          "timestamp_ms",
                          getTriggerMinutes(step.trigger) * 60000 +
                            Number((e.target as HTMLInputElement).value) * 1000,
                        )}
                    />
                    <span class="edit-unit">s</span>
                  {:else}
                    <input
                      class="edit-input-sm"
                      type="number"
                      value={step.trigger.temperature}
                      onchange={(e) =>
                        updateTriggerField(
                          i,
                          "temperature",
                          Number((e.target as HTMLInputElement).value),
                        )}
                    />
                    <span class="edit-unit">&deg;</span>
                    <select
                      class="edit-select"
                      value={step.trigger.direction}
                      onchange={(e) =>
                        updateTriggerField(
                          i,
                          "direction",
                          (e.target as HTMLSelectElement).value,
                        )}
                    >
                      <option value="rising">Rising</option>
                      <option value="falling">Falling</option>
                    </select>
                  {/if}
                </div>
                <div class="step-edit-actions">
                  <label class="edit-label">Actions</label>
                  {#each step.actions as action, j (j)}
                    <div class="action-row">
                      <input
                        class="edit-input"
                        type="text"
                        placeholder="channel"
                        value={action.channel}
                        onchange={(e) =>
                          updateActionChannel(
                            i,
                            j,
                            (e.target as HTMLInputElement).value,
                          )}
                      />
                      <span class="edit-unit">=</span>
                      <input
                        class="edit-input-sm"
                        type="number"
                        value={action.value}
                        onchange={(e) =>
                          updateActionValue(
                            i,
                            j,
                            Number((e.target as HTMLInputElement).value),
                          )}
                      />
                      {#if step.actions.length > 1}
                        <button
                          class="btn-remove-action"
                          onclick={() => removeAction(i, j)}>&times;</button
                        >
                      {/if}
                    </div>
                  {/each}
                  <button class="btn-add-action" onclick={() => addAction(i)}
                    >+ Action</button
                  >
                </div>
              </div>
            {/each}
            <button class="btn-add-step" onclick={addNewStep}>+ Add Step</button
            >
            {#if editSteps.length === 0}
              <p class="no-steps">No steps yet. Click "+ Add Step" above.</p>
            {/if}
          {:else}
            {#each selected.steps as step, i (step.id)}
              <div class="step-row">
                <span class="step-num">{i + 1}</span>
                <span class="step-trigger">{formatTrigger(step.trigger)}</span>
                <span class="step-actions">{formatActions(step.actions)}</span>
                <span class="step-enabled">{step.enabled ? "On" : "Off"}</span>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    </div>
  {/if}

  {#if loadingDetail}
    <div class="loading-overlay">Loading...</div>
  {/if}
</div>

<style>
  .cp-page {
    max-width: 900px;
    margin: 0 auto;
  }

  .page-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #e0e0e0;
    margin: 0 0 4px;
  }

  .page-desc {
    color: #888;
    font-size: 0.85rem;
    margin: 0 0 20px;
  }

  .loading {
    color: #888;
    text-align: center;
    padding: 40px;
  }

  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #666;
  }

  .hint {
    font-size: 0.85rem;
    color: #555;
  }

  .schedule-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .schedule-card {
    display: flex;
    align-items: center;
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    overflow: hidden;
    transition: border-color 0.15s;
  }

  .schedule-card:hover {
    border-color: #3a3a5a;
  }

  .schedule-card.selected {
    border-color: #4fc3f7;
  }

  .card-body {
    flex: 1;
    background: transparent;
    border: none;
    color: inherit;
    text-align: left;
    padding: 12px 16px;
    cursor: pointer;
    font: inherit;
  }

  .card-title {
    font-weight: 600;
    font-size: 0.95rem;
    color: #e0e0e0;
    margin-bottom: 4px;
  }

  .card-meta {
    font-size: 0.8rem;
    color: #888;
  }

  .sep {
    margin: 0 4px;
  }

  .card-actions {
    display: flex;
    gap: 4px;
    padding: 8px 12px;
    flex-shrink: 0;
  }

  .btn-delete {
    background: transparent;
    border: 1px solid transparent;
    color: #666;
    cursor: pointer;
    padding: 4px 6px;
    border-radius: 4px;
    font-size: 0.85rem;
  }

  .btn-delete:hover {
    color: #f44336;
    border-color: #f44336;
  }

  .btn-confirm-delete {
    background: #f44336;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 0.75rem;
    cursor: pointer;
  }

  .btn-cancel-delete {
    background: #2a2a4a;
    color: #ccc;
    border: none;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 0.75rem;
    cursor: pointer;
  }

  /* Detail panel */
  .detail-panel {
    margin-top: 20px;
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 10px;
    padding: 20px;
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    gap: 12px;
  }

  .detail-header h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #e0e0e0;
  }

  .edit-name {
    flex: 1;
    background: #0a0a1a;
    border: 1px solid #4fc3f7;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e0e0e0;
    font-size: 1rem;
    font-weight: 600;
  }

  .detail-actions {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-shrink: 0;
  }

  .btn-edit {
    background: rgba(79, 195, 247, 0.1);
    border: 1px solid #4fc3f7;
    color: #4fc3f7;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .btn-edit:hover {
    background: rgba(79, 195, 247, 0.2);
  }

  .btn-save {
    background: #2e7d32;
    border: none;
    color: white;
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .btn-save:hover {
    background: #388e3c;
  }

  .btn-save:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .btn-cancel {
    background: #2a2a4a;
    border: none;
    color: #ccc;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .btn-close {
    background: transparent;
    border: none;
    color: #666;
    font-size: 1.4rem;
    cursor: pointer;
    padding: 2px 6px;
    line-height: 1;
  }

  .btn-close:hover {
    color: #e0e0e0;
  }

  .detail-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 0.85rem;
    color: #aaa;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #2a2a4a;
  }

  .steps-section h4 {
    font-size: 0.9rem;
    color: #b0b0b0;
    margin: 0 0 8px;
    font-weight: 600;
  }

  .steps-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .step-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 10px;
    background: #1a1a3a;
    border-radius: 4px;
    font-size: 0.82rem;
  }

  .step-num {
    color: #666;
    font-size: 0.75rem;
    min-width: 18px;
  }

  .step-trigger {
    color: #4fc3f7;
    font-weight: 500;
    min-width: 100px;
  }

  .step-actions {
    color: #e6c229;
    flex: 1;
  }

  .step-enabled {
    color: #66bb6a;
    font-size: 0.75rem;
  }

  .step-edit-card {
    background: #1a1a3a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 6px;
  }

  .step-edit-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .btn-toggle-enabled {
    background: rgba(102, 187, 106, 0.15);
    border: 1px solid #66bb6a;
    color: #66bb6a;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.7rem;
    cursor: pointer;
  }

  .btn-toggle-enabled.off {
    background: rgba(102, 102, 102, 0.15);
    border-color: #666;
    color: #666;
  }

  .step-edit-trigger,
  .step-edit-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
  }

  .edit-label {
    font-size: 0.72rem;
    color: #888;
    min-width: 48px;
    font-weight: 600;
  }

  .edit-select {
    background: #0a0a1a;
    border: 1px solid #3a3a5a;
    border-radius: 4px;
    color: #e0e0e0;
    padding: 3px 6px;
    font-size: 0.78rem;
  }

  .edit-input {
    background: #0a0a1a;
    border: 1px solid #3a3a5a;
    border-radius: 4px;
    color: #e0e0e0;
    padding: 3px 6px;
    font-size: 0.78rem;
    width: 80px;
  }

  .edit-input-sm {
    background: #0a0a1a;
    border: 1px solid #3a3a5a;
    border-radius: 4px;
    color: #e0e0e0;
    padding: 3px 6px;
    font-size: 0.78rem;
    width: 50px;
  }

  .edit-unit {
    font-size: 0.75rem;
    color: #888;
  }

  .action-row {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .btn-remove-action {
    background: transparent;
    border: none;
    color: #666;
    cursor: pointer;
    font-size: 0.85rem;
    padding: 0 3px;
  }

  .btn-remove-action:hover {
    color: #f44336;
  }

  .btn-add-action {
    background: transparent;
    border: 1px dashed #3a3a5a;
    color: #888;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.7rem;
    cursor: pointer;
  }

  .btn-add-action:hover {
    border-color: #4fc3f7;
    color: #4fc3f7;
  }

  .btn-add-step {
    background: rgba(79, 195, 247, 0.08);
    border: 1px dashed #4fc3f7;
    color: #4fc3f7;
    border-radius: 6px;
    padding: 8px;
    font-size: 0.82rem;
    cursor: pointer;
    width: 100%;
    margin-top: 6px;
  }

  .btn-add-step:hover {
    background: rgba(79, 195, 247, 0.15);
  }

  .btn-remove-step {
    background: transparent;
    border: none;
    color: #666;
    cursor: pointer;
    font-size: 0.9rem;
    padding: 0 4px;
    margin-left: auto;
  }

  .btn-remove-step:hover {
    color: #f44336;
  }

  .no-steps {
    color: #666;
    font-size: 0.85rem;
    text-align: center;
    padding: 16px;
  }

  .loading-overlay {
    text-align: center;
    color: #888;
    padding: 20px;
  }

  @media (max-width: 480px) {
    .detail-meta {
      flex-direction: column;
      gap: 4px;
    }

    .step-row {
      flex-wrap: wrap;
      gap: 4px;
    }
  }
</style>
