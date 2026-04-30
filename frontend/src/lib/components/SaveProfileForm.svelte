<script lang="ts">
  interface Props {
    onsave: (data: {
      name: string;
      beanName: string;
      beanWeight: number;
    }) => void;
    oncancel?: () => void;
    saving?: boolean;
    saved?: boolean;
  }

  let { onsave, oncancel, saving = false, saved = false }: Props = $props();

  let name = $state("");
  let beanName = $state("");
  let beanWeight = $state(0);

  function handleSubmit(e: Event) {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) return;
    onsave({ name: trimmedName, beanName: beanName.trim(), beanWeight });
  }
</script>

<div class="save-form">
  <h4>Save Profile, Graph &amp; Controls</h4>
  {#if saved}
    <p class="saved-msg">Profile saved successfully.</p>
  {:else}
    <form onsubmit={handleSubmit}>
      <label class="field">
        <span class="label">Profile Name</span>
        <input
          type="text"
          bind:value={name}
          placeholder="e.g. Ethiopian Light"
        />
      </label>
      <label class="field">
        <span class="label">Bean Name</span>
        <input
          type="text"
          bind:value={beanName}
          placeholder="e.g. Yirgacheffe"
        />
      </label>
      <label class="field">
        <span class="label">Bean Weight (g)</span>
        <input type="number" bind:value={beanWeight} min="0" step="1" />
      </label>
      <div class="button-row">
        <button
          type="submit"
          class="btn-save"
          disabled={!name.trim() || saving}
        >
          {saving ? "Saving..." : "Save"}
        </button>
        {#if oncancel}
          <button type="button" class="btn-cancel" onclick={oncancel}>
            Cancel
          </button>
        {/if}
      </div>
    </form>
  {/if}
</div>

<style>
  .save-form {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
  }

  h4 {
    margin: 0 0 10px 0;
    color: var(--text);
    font-size: 0.85rem;
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  input {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 6px 8px;
    color: var(--text);
    font-size: 0.8rem;
  }

  input:focus {
    outline: none;
    border-color: var(--accent);
  }

  .button-row {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  .btn-save {
    background: #2e7d32;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-save:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .btn-cancel {
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .btn-cancel:hover {
    color: var(--text);
    border-color: var(--text-faint);
  }

  .saved-msg {
    color: #81c784;
    font-size: 0.85rem;
    margin: 0;
  }

  @media (max-width: 480px) {
    input {
      padding: 10px 12px;
    }

    .button-row {
      flex-direction: column;
    }

    .btn-save,
    .btn-cancel {
      padding: 10px 16px;
      width: 100%;
    }
  }
</style>
