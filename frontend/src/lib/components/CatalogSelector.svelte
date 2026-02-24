<script lang="ts">
  import {
    listManufacturers,
    listModels,
    createFromCatalog,
    createCustomMachine,
    updateMachine,
    type ManufacturerSummary,
    type CatalogModel,
    type SavedMachine,
  } from "$lib/services/machine-api";

  interface Props {
    open: boolean;
    onadd: (machine: SavedMachine) => void;
    onclose: () => void;
  }

  let { open, onadd, onclose }: Props = $props();

  type Step = "choose" | "manufacturer" | "model" | "confirm" | "custom";

  const PROTOCOLS = [
    { value: "modbus_tcp", label: "Modbus TCP" },
    { value: "modbus_rtu", label: "Modbus RTU" },
    { value: "serial", label: "Serial" },
    { value: "s7", label: "Siemens S7" },
  ];

  let step = $state<Step>("choose");
  let manufacturers = $state<ManufacturerSummary[]>([]);
  let models = $state<CatalogModel[]>([]);
  let selectedManufacturer = $state<ManufacturerSummary | null>(null);
  let selectedModel = $state<CatalogModel | null>(null);
  let customName = $state("");
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Custom machine form state
  let customProtocol = $state("modbus_tcp");
  let customHost = $state("192.168.1.1");
  let customPort = $state(502);

  // Catalog confirm step — editable connection fields
  let confirmHost = $state("");
  let confirmPort = $state(502);

  function reset() {
    step = "choose";
    manufacturers = [];
    models = [];
    selectedManufacturer = null;
    selectedModel = null;
    customName = "";
    customProtocol = "modbus_tcp";
    customHost = "192.168.1.1";
    customPort = 502;
    confirmHost = "";
    confirmPort = 502;
    loading = false;
    error = null;
  }

  function handleClose() {
    reset();
    onclose();
  }

  async function handleChooseCatalog() {
    loading = true;
    error = null;
    try {
      manufacturers = await listManufacturers();
      step = "manufacturer";
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load manufacturers";
    } finally {
      loading = false;
    }
  }

  function handleChooseCustom() {
    customName = "";
    customProtocol = "modbus_tcp";
    customHost = "192.168.1.1";
    customPort = 502;
    error = null;
    step = "custom";
  }

  async function handleSelectManufacturer(mfr: ManufacturerSummary) {
    selectedManufacturer = mfr;
    loading = true;
    error = null;
    try {
      models = await listModels(mfr.id);
      step = "model";
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load models";
    } finally {
      loading = false;
    }
  }

  function handleSelectModel(model: CatalogModel) {
    selectedModel = model;
    customName = model.name;
    const conn = model.connection ?? {};
    confirmHost =
      (conn as { host?: string }).host ??
      (conn as { comport?: string }).comport ??
      "";
    confirmPort =
      (conn as { port?: number }).port ??
      (conn as { baudrate?: number }).baudrate ??
      502;
    step = "confirm";
  }

  async function handleConfirm() {
    if (!selectedManufacturer || !selectedModel) return;
    loading = true;
    error = null;
    try {
      const result = await createFromCatalog(
        selectedManufacturer.id,
        selectedModel.id,
        customName.trim() || undefined,
      );

      // Patch the connection with user-provided host/port
      const conn = result.machine.connection ?? {};
      const isSerial = selectedModel.protocol === "serial";
      const updatedConn = isSerial
        ? { ...conn, comport: confirmHost, baudrate: confirmPort }
        : { ...conn, host: confirmHost, port: confirmPort };
      const patched = await updateMachine(result.id, {
        ...result.machine,
        connection: updatedConn,
      });
      onadd(patched);
      handleClose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to create machine";
      loading = false;
    }
  }

  function buildConnectionConfig(): Record<string, unknown> {
    if (customProtocol === "modbus_tcp") {
      return { type: "modbus_tcp", host: customHost, port: customPort };
    } else if (customProtocol === "modbus_rtu") {
      return { type: "modbus_rtu", host: customHost, port: customPort };
    } else if (customProtocol === "serial") {
      return {
        type: "serial",
        comport: customHost,
        baudrate: customPort,
      };
    } else {
      return { type: "s7", host: customHost, port: customPort };
    }
  }

  async function handleCustomConfirm() {
    if (!customName.trim()) return;
    loading = true;
    error = null;
    try {
      const result = await createCustomMachine({
        name: customName.trim(),
        protocol: customProtocol,
        connection: buildConnectionConfig(),
      });
      onadd(result.machine);
      handleClose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to create machine";
      loading = false;
    }
  }

  function handleBack() {
    error = null;
    if (step === "confirm") step = "model";
    else if (step === "model") step = "manufacturer";
    else if (step === "manufacturer" || step === "custom") step = "choose";
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") handleClose();
  }

  let hostLabel = $derived(
    customProtocol === "serial" ? "Serial Port" : "Host",
  );
  let portLabel = $derived(customProtocol === "serial" ? "Baudrate" : "Port");
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
      {#if step === "choose"}
        <h3>Add Machine</h3>
        <div class="choice-list">
          <button
            class="choice-btn"
            onclick={handleChooseCatalog}
            disabled={loading}
          >
            <span class="choice-icon">&#128218;</span>
            <span class="choice-text">
              <strong>From Catalog</strong>
              <small>Select from known machines</small>
            </span>
          </button>
          <button class="choice-btn" onclick={handleChooseCustom}>
            <span class="choice-icon">&#9998;</span>
            <span class="choice-text">
              <strong>Custom Machine</strong>
              <small>Configure manually</small>
            </span>
          </button>
        </div>
      {:else if step === "manufacturer"}
        <div class="step-header">
          <button class="btn-back" onclick={handleBack}>&larr;</button>
          <h3>Select Manufacturer</h3>
        </div>
        <div class="list-scroll">
          {#each manufacturers as mfr (mfr.id)}
            <button
              class="list-item"
              onclick={() => handleSelectManufacturer(mfr)}
              disabled={loading}
            >
              <span class="item-name">{mfr.name}</span>
              <span class="item-meta"
                >{mfr.country} &middot; {mfr.model_count} model{mfr.model_count !==
                1
                  ? "s"
                  : ""}</span
              >
            </button>
          {/each}
        </div>
      {:else if step === "model"}
        <div class="step-header">
          <button class="btn-back" onclick={handleBack}>&larr;</button>
          <h3>{selectedManufacturer?.name} &mdash; Select Model</h3>
        </div>
        <div class="list-scroll">
          {#each models as model (model.id)}
            <button
              class="list-item"
              onclick={() => handleSelectModel(model)}
              disabled={loading}
            >
              <span class="item-name">{model.name}</span>
              <span class="item-meta"
                >{model.protocol} &middot; {model.controls.length} control{model
                  .controls.length !== 1
                  ? "s"
                  : ""}</span
              >
            </button>
          {/each}
        </div>
      {:else if step === "confirm"}
        <div class="step-header">
          <button class="btn-back" onclick={handleBack}>&larr;</button>
          <h3>Confirm</h3>
        </div>
        <div class="confirm-details">
          <label class="field">
            <span class="label">Name</span>
            <!-- svelte-ignore a11y_autofocus -->
            <input type="text" bind:value={customName} autofocus />
          </label>
          <label class="field">
            <span class="label"
              >{selectedModel?.protocol === "serial"
                ? "Serial Port"
                : "Host"}</span
            >
            <input type="text" bind:value={confirmHost} />
          </label>
          <label class="field">
            <span class="label"
              >{selectedModel?.protocol === "serial"
                ? "Baudrate"
                : "Port"}</span
            >
            <input type="number" bind:value={confirmPort} min="1" />
          </label>
          <div class="detail-row">
            <span class="detail-label">Protocol</span>
            <span class="detail-value">{selectedModel?.protocol}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Controls</span>
            <span class="detail-value">
              {selectedModel?.controls.map((c) => c.name).join(", ") || "None"}
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Extra Channels</span>
            <span class="detail-value"
              >{selectedModel?.extra_channels.length ?? 0}</span
            >
          </div>
        </div>
        <div class="actions">
          <button class="btn-cancel" onclick={handleClose}>Cancel</button>
          <button
            class="btn-submit"
            onclick={handleConfirm}
            disabled={loading || !customName.trim()}
          >
            {loading ? "Creating..." : "Add Machine"}
          </button>
        </div>
      {:else if step === "custom"}
        <div class="step-header">
          <button class="btn-back" onclick={handleBack}>&larr;</button>
          <h3>Custom Machine</h3>
        </div>
        <div class="confirm-details">
          <label class="field">
            <span class="label">Machine Name</span>
            <!-- svelte-ignore a11y_autofocus -->
            <input
              type="text"
              bind:value={customName}
              placeholder="My Roaster"
              autofocus
            />
          </label>
          <label class="field">
            <span class="label">Protocol</span>
            <select bind:value={customProtocol}>
              {#each PROTOCOLS as proto (proto.value)}
                <option value={proto.value}>{proto.label}</option>
              {/each}
            </select>
          </label>
          <label class="field">
            <span class="label">{hostLabel}</span>
            <input type="text" bind:value={customHost} />
          </label>
          <label class="field">
            <span class="label">{portLabel}</span>
            <input type="number" bind:value={customPort} min="1" />
          </label>
        </div>
        <div class="actions">
          <button class="btn-cancel" onclick={handleClose}>Cancel</button>
          <button
            class="btn-submit"
            onclick={handleCustomConfirm}
            disabled={loading || !customName.trim()}
          >
            {loading ? "Creating..." : "Create Machine"}
          </button>
        </div>
      {/if}

      {#if error}
        <div class="error-msg">{error}</div>
      {/if}

      {#if step !== "confirm" && step !== "custom"}
        <div class="actions">
          <button class="btn-cancel" onclick={handleClose}>Cancel</button>
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
    min-width: 360px;
    max-width: 480px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  h3 {
    margin: 0;
    color: #e0e0e0;
    font-size: 1rem;
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

  .choice-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .choice-btn {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 14px 16px;
    color: #e0e0e0;
    cursor: pointer;
    text-align: left;
  }

  .choice-btn:hover:not(:disabled) {
    border-color: #4fc3f7;
  }

  .choice-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .choice-icon {
    font-size: 1.5rem;
  }

  .choice-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .choice-text strong {
    font-size: 0.9rem;
  }

  .choice-text small {
    font-size: 0.75rem;
    color: #999;
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

  .item-name {
    font-size: 0.9rem;
    font-weight: 500;
  }

  .item-meta {
    font-size: 0.75rem;
    color: #999;
  }

  .confirm-details {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .label {
    font-size: 0.75rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  input,
  select {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e0e0e0;
    font-size: 0.9rem;
  }

  input:focus,
  select:focus {
    outline: none;
    border-color: #4fc3f7;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 0.85rem;
  }

  .detail-label {
    color: #999;
  }

  .detail-value {
    color: #e0e0e0;
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

  .btn-submit {
    background: #2e7d32;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-submit:disabled {
    opacity: 0.4;
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
</style>
