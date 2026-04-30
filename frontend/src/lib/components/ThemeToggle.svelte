<script lang="ts">
  import { theme } from "$lib/stores/theme.svelte";
  let current = $derived(theme.value);
</script>

<button
  class="theme-toggle"
  type="button"
  aria-label={current === "dark"
    ? "Switch to light theme"
    : "Switch to dark theme"}
  title={current === "dark" ? "Switch to light theme" : "Switch to dark theme"}
  onclick={() => theme.toggle()}
>
  {#if current === "dark"}
    <!-- sun icon -->
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <circle cx="12" cy="12" r="4.2" fill="currentColor" />
      <g stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
        <line x1="12" y1="2.4" x2="12" y2="5" />
        <line x1="12" y1="19" x2="12" y2="21.6" />
        <line x1="2.4" y1="12" x2="5" y2="12" />
        <line x1="19" y1="12" x2="21.6" y2="12" />
        <line x1="5.2" y1="5.2" x2="7" y2="7" />
        <line x1="17" y1="17" x2="18.8" y2="18.8" />
        <line x1="5.2" y1="18.8" x2="7" y2="17" />
        <line x1="17" y1="7" x2="18.8" y2="5.2" />
      </g>
    </svg>
  {:else}
    <!-- moon icon -->
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        d="M20.5 14.2A8 8 0 0 1 9.8 3.5a.6.6 0 0 0-.8-.7 9.5 9.5 0 1 0 12.2 12.2.6.6 0 0 0-.7-.8z"
        fill="currentColor"
      />
    </svg>
  {/if}
</button>

<style>
  .theme-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    padding: 0;
    background: transparent;
    border: 1px solid var(--border, transparent);
    border-radius: 6px;
    color: var(--text-muted, var(--text-muted));
    cursor: pointer;
    transition:
      background 0.15s,
      color 0.15s,
      border-color 0.15s;
  }

  .theme-toggle:hover {
    color: var(--accent, var(--accent));
    background: var(--surface-hover, rgba(255, 255, 255, 0.06));
  }

  .theme-toggle:focus-visible {
    outline: 2px solid var(--accent, var(--accent));
    outline-offset: 2px;
  }
</style>
