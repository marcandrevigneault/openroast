<script lang="ts">
  interface Props {
    open: boolean;
    onadd: (name: string) => void;
    onclose: () => void;
  }

  let { open, onadd, onclose }: Props = $props();
  let name = $state("");

  function handleSubmit(e: Event) {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed) {
      onadd(trimmed);
      name = "";
      onclose();
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      onclose();
    }
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_interactive_supports_focus a11y_autofocus -->
  <div
    class="overlay"
    role="dialog"
    aria-modal="true"
    onkeydown={handleKeydown}
  >
    <div class="dialog">
      <h3>Add Machine</h3>
      <form onsubmit={handleSubmit}>
        <label class="field">
          <span class="label">Machine Name</span>
          <!-- svelte-ignore a11y_autofocus -->
          <input
            type="text"
            bind:value={name}
            placeholder="e.g. Stratto Pro 300"
            autofocus
          />
        </label>
        <div class="actions">
          <button type="button" class="btn-cancel" onclick={onclose}
            >Cancel</button
          >
          <button type="submit" class="btn-submit" disabled={!name.trim()}
            >Add</button
          >
        </div>
      </form>
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
    min-width: 300px;
  }

  h3 {
    margin: 0 0 16px 0;
    color: #e0e0e0;
    font-size: 1rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 16px;
  }

  .label {
    font-size: 0.75rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  input {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e0e0e0;
    font-size: 0.9rem;
  }

  input:focus {
    outline: none;
    border-color: #4fc3f7;
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
</style>
