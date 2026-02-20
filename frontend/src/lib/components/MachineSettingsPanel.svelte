<script lang="ts">
  import {
    getMachine,
    updateMachine,
    type SavedMachine,
    type CatalogControl,
  } from "$lib/services/machine-api";

  interface Props {
    machineId: string;
    open: boolean;
    onclose: () => void;
    onsaved: (machine: SavedMachine) => void;
  }

  let { machineId, open, onclose, onsaved }: Props = $props();

  const PROTOCOLS = [
    { value: "modbus_tcp", label: "Modbus TCP" },
    { value: "modbus_rtu", label: "Modbus RTU" },
    { value: "serial", label: "Serial" },
    { value: "s7", label: "Siemens S7" },
  ];

  let loading = $state(false);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let machine = $state<SavedMachine | null>(null);

  // Editable fields
  let name = $state("");
  let protocol = $state("modbus_tcp");
  let host = $state("");
  let port = $state(502);
  let samplingInterval = $state(3000);
  let controls = $state<CatalogControl[]>([]);
  let extraChannels = $state<Record<string, unknown>[]>([]);
  let etSensor = $state<Record<string, unknown>>({});
  let btSensor = $state<Record<string, unknown>>({});

  let isSerial = $derived(protocol === "serial");
  let isModbus = $derived(
    protocol === "modbus_tcp" || protocol === "modbus_rtu",
  );
  let isS7 = $derived(protocol === "s7");

  $effect(() => {
    if (open && machineId && !machine) {
      loadMachine();
    }
  });

  async function loadMachine() {
    loading = true;
    error = null;
    try {
      const m = await getMachine(machineId);
      machine = m;
      name = m.name;
      protocol = m.protocol;
      samplingInterval = m.sampling_interval_ms;
      controls = [...(m.controls ?? [])];
      extraChannels = (m.extra_channels ?? []).map((ch) => ({ ...ch }));

      // Load sensor configs
      etSensor = (m as Record<string, unknown>).et
        ? { ...((m as Record<string, unknown>).et as Record<string, unknown>) }
        : { name: "ET" };
      btSensor = (m as Record<string, unknown>).bt
        ? { ...((m as Record<string, unknown>).bt as Record<string, unknown>) }
        : { name: "BT" };

      // Extract connection params
      const conn = m.connection ?? {};
      if (protocol === "serial") {
        host = (conn as { comport?: string }).comport ?? "/dev/ttyUSB0";
        port = (conn as { baudrate?: number }).baudrate ?? 115200;
      } else {
        host = (conn as { host?: string }).host ?? "192.168.1.1";
        port = (conn as { port?: number }).port ?? 502;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load machine";
    } finally {
      loading = false;
    }
  }

  function buildConnectionConfig(): Record<string, unknown> {
    if (protocol === "modbus_tcp") {
      return { type: "modbus_tcp", host, port };
    } else if (protocol === "modbus_rtu") {
      return { type: "modbus_rtu", host, port };
    } else if (protocol === "serial") {
      return { type: "serial", comport: host, baudrate: port };
    } else {
      return { type: "s7", host, port };
    }
  }

  function getModbus(
    obj: Record<string, unknown>,
  ): Record<string, unknown> | null {
    return (obj.modbus as Record<string, unknown>) ?? null;
  }

  function getS7(obj: Record<string, unknown>): Record<string, unknown> | null {
    return (obj.s7 as Record<string, unknown>) ?? null;
  }

  async function handleSave() {
    if (!machine || !name.trim()) return;
    saving = true;
    error = null;
    try {
      const updated: SavedMachine = {
        ...machine,
        name: name.trim(),
        protocol,
        connection: buildConnectionConfig(),
        sampling_interval_ms: samplingInterval,
        controls,
        extra_channels: extraChannels.filter(
          (ch) => ((ch as { name?: string }).name ?? "").trim() !== "",
        ),
        et: etSensor,
        bt: btSensor,
      };
      const result = await updateMachine(machineId, updated);
      onsaved(result);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to save";
    } finally {
      saving = false;
    }
  }

  function addControl() {
    controls = [
      ...controls,
      {
        name: "",
        channel: "",
        command: "",
        min: 0,
        max: 100,
        step: 1,
        unit: "",
      },
    ];
  }

  function removeControl(index: number) {
    controls = controls.filter((_, i) => i !== index);
  }

  function addExtraChannel() {
    let newChannel: Record<string, unknown> = { name: "" };
    if (isModbus) {
      newChannel.modbus = {
        address: 0,
        code: 3,
        device_id: 1,
        divisor: 0,
        mode: "",
        is_float: false,
        is_bcd: false,
      };
    } else if (isS7) {
      newChannel.s7 = {
        area: 0,
        db_nr: 0,
        start: 0,
        type: 0,
        mode: 0,
        div: 0,
      };
    }
    extraChannels = [...extraChannels, newChannel];
  }

  function removeExtraChannel(index: number) {
    extraChannels = extraChannels.filter((_, i) => i !== index);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
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
      <div class="dialog-header">
        <h3>Machine Settings</h3>
        <button class="btn-close" onclick={onclose}>&times;</button>
      </div>

      {#if loading}
        <div class="loading">Loading...</div>
      {:else if error && !machine}
        <div class="error-msg">{error}</div>
      {:else if machine}
        <div class="form-scroll">
          <!-- General -->
          <section class="form-section">
            <h4>General</h4>
            <label class="field">
              <span class="label">Name</span>
              <input type="text" bind:value={name} />
            </label>
            <label class="field">
              <span class="label">Protocol</span>
              <select bind:value={protocol}>
                {#each PROTOCOLS as p (p.value)}
                  <option value={p.value}>{p.label}</option>
                {/each}
              </select>
            </label>
            <label class="field">
              <span class="label">Sampling Interval (ms)</span>
              <input
                type="number"
                bind:value={samplingInterval}
                min="500"
                max="10000"
                step="100"
              />
            </label>
          </section>

          <div class="section-divider"></div>

          <!-- Connection -->
          <section class="form-section">
            <h4>Connection</h4>
            <label class="field">
              <span class="label">{isSerial ? "Serial Port" : "Host"}</span>
              <input type="text" bind:value={host} />
            </label>
            <label class="field">
              <span class="label">{isSerial ? "Baudrate" : "Port"}</span>
              <input type="number" bind:value={port} min="1" />
            </label>
          </section>

          <div class="section-divider"></div>

          <!-- Sensors (BT / ET) -->
          <section class="form-section">
            <h4>Sensors</h4>

            <!-- BT -->
            <div class="list-item-card">
              <div class="item-row">
                <label class="field field-sm">
                  <span class="label">BT Name</span>
                  <input type="text" bind:value={btSensor.name} />
                </label>
              </div>
              {#if isModbus && getModbus(btSensor)}
                {@const mb = getModbus(btSensor)!}
                <div class="item-row">
                  <label class="field field-sm">
                    <span class="label">Address</span>
                    <input type="number" bind:value={mb.address} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Fn Code</span>
                    <input type="number" bind:value={mb.code} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Device ID</span>
                    <input type="number" bind:value={mb.device_id} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Divisor</span>
                    <input type="number" bind:value={mb.divisor} />
                  </label>
                </div>
              {/if}
              {#if isS7 && getS7(btSensor)}
                {@const s7 = getS7(btSensor)!}
                <div class="item-row">
                  <label class="field field-sm">
                    <span class="label">DB Nr</span>
                    <input type="number" bind:value={s7.db_nr} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Start</span>
                    <input type="number" bind:value={s7.start} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Area</span>
                    <input type="number" bind:value={s7.area} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Div</span>
                    <input type="number" bind:value={s7.div} />
                  </label>
                </div>
              {/if}
            </div>

            <!-- ET -->
            <div class="list-item-card">
              <div class="item-row">
                <label class="field field-sm">
                  <span class="label">ET Name</span>
                  <input type="text" bind:value={etSensor.name} />
                </label>
              </div>
              {#if isModbus && getModbus(etSensor)}
                {@const mb = getModbus(etSensor)!}
                <div class="item-row">
                  <label class="field field-sm">
                    <span class="label">Address</span>
                    <input type="number" bind:value={mb.address} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Fn Code</span>
                    <input type="number" bind:value={mb.code} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Device ID</span>
                    <input type="number" bind:value={mb.device_id} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Divisor</span>
                    <input type="number" bind:value={mb.divisor} />
                  </label>
                </div>
              {/if}
              {#if isS7 && getS7(etSensor)}
                {@const s7 = getS7(etSensor)!}
                <div class="item-row">
                  <label class="field field-sm">
                    <span class="label">DB Nr</span>
                    <input type="number" bind:value={s7.db_nr} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Start</span>
                    <input type="number" bind:value={s7.start} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Area</span>
                    <input type="number" bind:value={s7.area} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Div</span>
                    <input type="number" bind:value={s7.div} />
                  </label>
                </div>
              {/if}
            </div>
          </section>

          <div class="section-divider"></div>

          <!-- Controls -->
          <section class="form-section">
            <div class="section-header">
              <h4>Controls</h4>
              <button class="btn-add" onclick={addControl}>+ Add</button>
            </div>
            {#each controls as ctrl, i (i)}
              <div class="list-item-card">
                <div class="item-row">
                  <label class="field field-sm">
                    <span class="label">Name</span>
                    <input type="text" bind:value={ctrl.name} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Channel</span>
                    <input type="text" bind:value={ctrl.channel} />
                  </label>
                  <button
                    class="btn-remove-item"
                    onclick={() => removeControl(i)}
                    title="Remove control">&times;</button
                  >
                </div>
                <div class="item-row">
                  <label class="field field-sm">
                    <span class="label">Min</span>
                    <input type="number" bind:value={ctrl.min} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Max</span>
                    <input type="number" bind:value={ctrl.max} />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Step</span>
                    <input type="number" bind:value={ctrl.step} min="0.1" />
                  </label>
                  <label class="field field-sm">
                    <span class="label">Unit</span>
                    <input type="text" bind:value={ctrl.unit} />
                  </label>
                </div>
                <label class="field">
                  <span class="label">Command</span>
                  <input
                    type="text"
                    bind:value={ctrl.command}
                    placeholder={"writeSingle(1,47,{})"}
                  />
                </label>
              </div>
            {/each}
            {#if controls.length === 0}
              <p class="empty-hint">No controls configured.</p>
            {/if}
          </section>

          <div class="section-divider"></div>

          <!-- Extra Channels -->
          <section class="form-section">
            <div class="section-header">
              <h4>Extra Channels</h4>
              <button class="btn-add" onclick={addExtraChannel}>+ Add</button>
            </div>
            {#each extraChannels as _ch, i (i)}
              <div class="list-item-card">
                <div class="item-row">
                  <label class="field field-sm">
                    <span class="label">Name</span>
                    <input
                      type="text"
                      bind:value={extraChannels[i].name}
                      placeholder="Channel name"
                    />
                  </label>
                  <button
                    class="btn-remove-item"
                    onclick={() => removeExtraChannel(i)}
                    title="Remove channel">&times;</button
                  >
                </div>
                {#if isModbus && getModbus(extraChannels[i])}
                  {@const mb = getModbus(extraChannels[i])!}
                  <div class="item-row">
                    <label class="field field-sm">
                      <span class="label">Address</span>
                      <input type="number" bind:value={mb.address} />
                    </label>
                    <label class="field field-sm">
                      <span class="label">Fn Code</span>
                      <input type="number" bind:value={mb.code} />
                    </label>
                    <label class="field field-sm">
                      <span class="label">Device ID</span>
                      <input type="number" bind:value={mb.device_id} />
                    </label>
                    <label class="field field-sm">
                      <span class="label">Divisor</span>
                      <input type="number" bind:value={mb.divisor} />
                    </label>
                  </div>
                {/if}
                {#if isS7 && getS7(extraChannels[i])}
                  {@const s7 = getS7(extraChannels[i])!}
                  <div class="item-row">
                    <label class="field field-sm">
                      <span class="label">DB Nr</span>
                      <input type="number" bind:value={s7.db_nr} />
                    </label>
                    <label class="field field-sm">
                      <span class="label">Start</span>
                      <input type="number" bind:value={s7.start} />
                    </label>
                    <label class="field field-sm">
                      <span class="label">Area</span>
                      <input type="number" bind:value={s7.area} />
                    </label>
                    <label class="field field-sm">
                      <span class="label">Div</span>
                      <input type="number" bind:value={s7.div} />
                    </label>
                  </div>
                {/if}
              </div>
            {/each}
            {#if extraChannels.length === 0}
              <p class="empty-hint">No extra channels configured.</p>
            {/if}
          </section>
        </div>

        {#if error}
          <div class="error-msg">{error}</div>
        {/if}

        <div class="actions">
          <button class="btn-cancel" onclick={onclose}>Cancel</button>
          <button
            class="btn-submit"
            onclick={handleSave}
            disabled={saving || !name.trim()}
          >
            {saving ? "Saving..." : "Save"}
          </button>
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
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  h3 {
    margin: 0;
    color: #e0e0e0;
    font-size: 1rem;
  }

  .btn-close {
    background: transparent;
    border: none;
    color: #888;
    font-size: 1.2rem;
    cursor: pointer;
    padding: 0 4px;
  }

  .btn-close:hover {
    color: #e0e0e0;
  }

  .form-scroll {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-height: 60vh;
    padding-right: 4px;
  }

  .form-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .section-divider {
    border-top: 1px solid #2a2a4a;
  }

  h4 {
    margin: 0;
    color: #ccc;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid #2a2a4a;
    padding-bottom: 4px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #2a2a4a;
    padding-bottom: 4px;
  }

  .section-header h4 {
    border-bottom: none;
    padding-bottom: 0;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .field-sm {
    flex: 1;
    min-width: 0;
  }

  .label {
    font-size: 0.7rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  input,
  select {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    padding: 6px 10px;
    color: #e0e0e0;
    font-size: 0.85rem;
  }

  input:focus,
  select:focus {
    outline: none;
    border-color: #4fc3f7;
  }

  .btn-add {
    background: transparent;
    border: 1px solid #2a2a4a;
    color: #4fc3f7;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.75rem;
    cursor: pointer;
  }

  .btn-add:hover {
    border-color: #4fc3f7;
  }

  .list-item-card {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .item-row {
    display: flex;
    gap: 8px;
    align-items: flex-end;
  }

  .btn-remove-item {
    background: transparent;
    border: 1px solid transparent;
    color: #666;
    font-size: 1rem;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1;
    flex-shrink: 0;
  }

  .btn-remove-item:hover {
    color: #f44336;
    border-color: #f44336;
  }

  .empty-hint {
    color: #666;
    font-size: 0.8rem;
    font-style: italic;
    margin: 0;
  }

  .loading {
    text-align: center;
    color: #888;
    padding: 24px 0;
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
