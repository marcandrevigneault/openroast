<script lang="ts">
  import { onMount } from "svelte";
  import {
    listSimulators,
    startSimulator,
    stopSimulator,
    type SimulatorInfo,
  } from "$lib/services/simulator-api";
  import {
    listManufacturers,
    listModels,
    type ManufacturerSummary,
    type CatalogModel,
  } from "$lib/services/machine-api";
  import { addToast } from "$lib/stores/toast";
  import ToastContainer from "$lib/components/ToastContainer.svelte";

  let simulators = $state<SimulatorInfo[]>([]);
  let loading = $state(true);
  let showAddDialog = $state(false);
  let confirmStopId = $state<string | null>(null);

  // Add-simulator dialog state
  type AddStep = "manufacturer" | "model" | "confirm";
  let addStep = $state<AddStep>("manufacturer");
  let manufacturers = $state<ManufacturerSummary[]>([]);
  let models = $state<CatalogModel[]>([]);
  let selectedManufacturer = $state<ManufacturerSummary | null>(null);
  let selectedModel = $state<CatalogModel | null>(null);
  let customName = $state("");
  let customPort = $state(0);
  let addLoading = $state(false);
  let addError = $state<string | null>(null);

  async function loadSimulators() {
    try {
      simulators = await listSimulators();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load simulators";
      addToast(msg, "error");
    } finally {
      loading = false;
    }
  }

  async function handleStop(machineId: string) {
    try {
      await stopSimulator(machineId);
      simulators = simulators.filter((s) => s.machine_id !== machineId);
      confirmStopId = null;
      addToast("Simulator stopped", "info");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to stop simulator";
      addToast(msg, "error");
    }
  }

  async function openAddDialog() {
    showAddDialog = true;
    addStep = "manufacturer";
    addError = null;
    addLoading = true;
    selectedManufacturer = null;
    selectedModel = null;
    customName = "";
    customPort = 0;
    try {
      manufacturers = await listManufacturers();
    } catch (e) {
      addError = e instanceof Error ? e.message : "Failed to load catalog";
    } finally {
      addLoading = false;
    }
  }

  function closeAddDialog() {
    showAddDialog = false;
    addError = null;
    manufacturers = [];
    models = [];
    selectedManufacturer = null;
    selectedModel = null;
  }

  async function handleSelectManufacturer(mfr: ManufacturerSummary) {
    selectedManufacturer = mfr;
    addLoading = true;
    addError = null;
    try {
      models = await listModels(mfr.id);
      addStep = "model";
    } catch (e) {
      addError = e instanceof Error ? e.message : "Failed to load models";
    } finally {
      addLoading = false;
    }
  }

  function handleSelectModel(model: CatalogModel) {
    selectedModel = model;
    customName = model.name;
    customPort = 0;
    addError = null;
    addStep = "confirm";
  }

  async function handleConfirmStart() {
    if (!selectedManufacturer || !selectedModel) return;
    addLoading = true;
    addError = null;
    try {
      const info = await startSimulator({
        manufacturer_id: selectedManufacturer.id,
        model_id: selectedModel.id,
        port: customPort || undefined,
        name: customName || undefined,
      });
      simulators = [...simulators, info];
      closeAddDialog();
      addToast(`Simulator started: ${info.name} on port ${info.port}`, "info");
    } catch (e) {
      addError = e instanceof Error ? e.message : "Failed to start simulator";
      addLoading = false;
    }
  }

  function handleAddBack() {
    addError = null;
    if (addStep === "confirm") addStep = "model";
    else if (addStep === "model") addStep = "manufacturer";
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") closeAddDialog();
  }

  onMount(loadSimulators);
</script>

<svelte:head>
  <title>Simulator - OpenRoast</title>
</svelte:head>

<div class="page">
  <div class="page-header">
    <h2>Simulator</h2>
    <button class="btn-add" onclick={openAddDialog}>+ New Simulator</button>
  </div>

  {#if loading}
    <div class="loading">Loading simulators...</div>
  {:else if simulators.length === 0}
    <div class="empty-state">
      <p class="empty-title">No simulators running</p>
      <p class="empty-desc">
        Start a simulated machine to test without hardware. The simulator
        creates a virtual Modbus TCP server that responds like a real roaster.
      </p>
      <button class="btn-add" onclick={openAddDialog}>+ Start Simulator</button>
    </div>
  {:else}
    <div class="sim-grid">
      {#each simulators as sim (sim.machine_id)}
        <div class="sim-card">
          <div class="sim-header">
            <span class="sim-status">Running</span>
          </div>
          <h3 class="sim-name">{sim.name}</h3>
          <div class="sim-details">
            <div class="detail-row">
              <span class="detail-label">Host</span>
              <span class="detail-value">{sim.host}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Port</span>
              <span class="detail-value">{sim.port}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Machine ID</span>
              <span class="detail-value mono"
                >{sim.machine_id.slice(0, 8)}...</span
              >
            </div>
            <div class="detail-row">
              <span class="detail-label">Catalog</span>
              <span class="detail-value">{sim.catalog_id}</span>
            </div>
          </div>
          <div class="sim-actions">
            {#if confirmStopId === sim.machine_id}
              <span class="confirm-text">Stop this simulator?</span>
              <button
                class="btn-confirm-stop"
                onclick={() => handleStop(sim.machine_id)}
              >
                Yes, stop
              </button>
              <button
                class="btn-cancel-stop"
                onclick={() => (confirmStopId = null)}
              >
                Cancel
              </button>
            {:else}
              <button
                class="btn-stop"
                onclick={() => (confirmStopId = sim.machine_id)}
              >
                Stop
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Add Simulator Dialog -->
{#if showAddDialog}
  <!-- svelte-ignore a11y_interactive_supports_focus -->
  <div
    class="overlay"
    role="dialog"
    aria-modal="true"
    onkeydown={handleKeydown}
  >
    <div class="dialog">
      {#if addStep === "manufacturer"}
        <h3>Start Simulator</h3>
        <p class="dialog-desc">
          Select a machine from the catalog to simulate.
        </p>
        {#if addLoading}
          <div class="loading">Loading catalog...</div>
        {:else}
          <div class="list-scroll">
            {#each manufacturers as mfr (mfr.id)}
              <button
                class="list-item"
                onclick={() => handleSelectManufacturer(mfr)}
              >
                <span class="item-name">{mfr.name}</span>
                <span class="item-meta">
                  {mfr.country} &middot; {mfr.model_count} model{mfr.model_count !==
                  1
                    ? "s"
                    : ""}
                </span>
              </button>
            {/each}
          </div>
        {/if}
      {:else if addStep === "model"}
        <div class="step-header">
          <button class="btn-back" onclick={handleAddBack}>&larr;</button>
          <h3>{selectedManufacturer?.name}</h3>
        </div>
        {#if addLoading}
          <div class="loading">Loading models...</div>
        {:else}
          <div class="list-scroll">
            {#each models as model (model.id)}
              <button
                class="list-item"
                onclick={() => handleSelectModel(model)}
              >
                <span class="item-name">{model.name}</span>
                <span class="item-meta">
                  {model.protocol} &middot;
                  {model.controls.length} control{model.controls.length !== 1
                    ? "s"
                    : ""}
                  &middot; {model.sampling_interval_ms}ms sampling
                </span>
              </button>
            {/each}
          </div>
        {/if}
      {:else if addStep === "confirm"}
        <div class="step-header">
          <button class="btn-back" onclick={handleAddBack}>&larr;</button>
          <h3>Configure Simulator</h3>
        </div>
        <div class="form-fields">
          <label class="form-label">
            <span>Name</span>
            <input
              class="form-input"
              type="text"
              bind:value={customName}
              placeholder={selectedModel?.name}
            />
          </label>
          <label class="form-label">
            <span>Port</span>
            <input
              class="form-input"
              type="number"
              bind:value={customPort}
              min="0"
              max="65535"
              placeholder="Auto"
            />
            <span class="form-hint">0 = auto-assign a free port</span>
          </label>
        </div>
        <button
          class="btn-start"
          onclick={handleConfirmStart}
          disabled={addLoading}
        >
          {addLoading ? "Starting..." : "Start Simulator"}
        </button>
      {/if}

      {#if addError}
        <div class="error-msg">{addError}</div>
      {/if}

      <div class="actions">
        <button class="btn-cancel" onclick={closeAddDialog}>Cancel</button>
      </div>
    </div>
  </div>
{/if}

<ToastContainer />

<style>
  .page {
    padding: 16px 20px;
    max-width: 900px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }

  .page-header h2 {
    margin: 0;
    color: #f5f0e8;
    font-size: 1.2rem;
    font-weight: 700;
  }

  .btn-add {
    background: rgba(79, 195, 247, 0.1);
    border: 1px solid #4fc3f7;
    color: #4fc3f7;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-add:hover {
    background: rgba(79, 195, 247, 0.2);
  }

  .loading {
    text-align: center;
    color: #888;
    padding: 40px 20px;
  }

  .empty-state {
    text-align: center;
    padding: 60px 20px;
  }

  .empty-title {
    color: #ccc;
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0 0 8px;
  }

  .empty-desc {
    color: #888;
    font-size: 0.85rem;
    margin: 0 0 20px;
    max-width: 400px;
    margin-inline: auto;
    line-height: 1.5;
  }

  /* ── Simulator cards ─────────────────────────────────────────────── */

  .sim-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }

  .sim-card {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 10px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .sim-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .sim-status {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #66bb6a;
    background: rgba(102, 187, 106, 0.1);
    padding: 2px 8px;
    border-radius: 4px;
  }

  .sim-name {
    margin: 0;
    color: #e0e0e0;
    font-size: 1rem;
    font-weight: 600;
  }

  .sim-details {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 0;
    border-top: 1px solid #2a2a4a;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
  }

  .detail-label {
    color: #888;
  }

  .detail-value {
    color: #ccc;
  }

  .detail-value.mono {
    font-family: monospace;
    font-size: 0.75rem;
  }

  .sim-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-top: 8px;
    border-top: 1px solid #2a2a4a;
  }

  .confirm-text {
    font-size: 0.8rem;
    color: #ff8a80;
    flex: 1;
  }

  .btn-stop {
    background: rgba(244, 67, 54, 0.1);
    border: 1px solid #f44336;
    color: #f44336;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.8rem;
    cursor: pointer;
    margin-left: auto;
  }

  .btn-stop:hover {
    background: rgba(244, 67, 54, 0.2);
  }

  .btn-confirm-stop {
    background: #f44336;
    border: none;
    color: white;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-cancel-stop {
    background: #2a2a4a;
    border: none;
    color: #ccc;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  /* ── Add Dialog ──────────────────────────────────────────────────── */

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
    min-width: 360px;
    max-width: 480px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .dialog h3 {
    margin: 0;
    color: #e0e0e0;
    font-size: 1rem;
  }

  .dialog-desc {
    margin: 0;
    color: #888;
    font-size: 0.8rem;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .btn-back {
    background: transparent;
    border: 1px solid #2a2a4a;
    color: #ccc;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 1rem;
    cursor: pointer;
  }

  .btn-back:hover {
    border-color: #4fc3f7;
    color: #4fc3f7;
  }

  .list-scroll {
    max-height: 300px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .list-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 10px 14px;
    color: #e0e0e0;
    cursor: pointer;
    text-align: left;
  }

  .list-item:hover:not(:disabled) {
    border-color: #4fc3f7;
  }

  .list-item:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .item-name {
    font-size: 0.9rem;
    font-weight: 500;
  }

  .item-meta {
    font-size: 0.75rem;
    color: #999;
  }

  .form-fields {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .form-label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 0.8rem;
    color: #b0b0b0;
  }

  .form-input {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e0e0e0;
    font-size: 0.85rem;
  }

  .form-input:focus {
    outline: none;
    border-color: #4fc3f7;
  }

  .form-hint {
    font-size: 0.7rem;
    color: #666;
  }

  .btn-start {
    background: rgba(79, 195, 247, 0.15);
    border: 1px solid #4fc3f7;
    color: #4fc3f7;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-start:hover:not(:disabled) {
    background: rgba(79, 195, 247, 0.25);
  }

  .btn-start:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-msg {
    background: #3e1111;
    border: 1px solid #f44336;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ff8a80;
    font-size: 0.8rem;
  }

  .actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .btn-cancel {
    background: #2a2a4a;
    color: #ccc;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  @media (max-width: 480px) {
    .page {
      padding: 12px;
    }

    .sim-grid {
      grid-template-columns: 1fr;
    }

    .dialog {
      min-width: 0;
      width: 95vw;
      max-width: none;
      max-height: 90vh;
      padding: 16px;
    }

    .list-scroll {
      max-height: 50vh;
    }
  }
</style>
