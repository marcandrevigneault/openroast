<script lang="ts">
  import {
    getToasts,
    subscribe,
    dismissToast,
    type Toast,
  } from "$lib/stores/toast";

  let toasts = $state<Toast[]>(getToasts());

  $effect(() => {
    const unsub = subscribe(() => {
      toasts = getToasts();
    });
    return unsub;
  });
</script>

{#if toasts.length > 0}
  <div class="toast-container" role="status" aria-live="polite">
    {#each toasts as toast (toast.id)}
      <div class="toast toast-{toast.type}">
        <div class="toast-content">
          {#if toast.machineLabel}
            <span class="toast-machine">{toast.machineLabel}</span>
          {/if}
          <span class="toast-message">{toast.message}</span>
        </div>
        <button
          class="toast-dismiss"
          onclick={() => dismissToast(toast.id)}
          aria-label="Dismiss">&times;</button
        >
      </div>
    {/each}
  </div>
{/if}

<style>
  .toast-container {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 200;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 400px;
    pointer-events: none;
  }

  .toast {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 0.85rem;
    pointer-events: auto;
    animation: slideIn 0.2s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateX(20px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  .toast-error {
    background: #3e1111;
    border: 1px solid #f44336;
    color: #ff8a80;
  }

  .toast-warning {
    background: #3e2e11;
    border: 1px solid #ff9800;
    color: #ffcc80;
  }

  .toast-info {
    background: #112e3e;
    border: 1px solid #4fc3f7;
    color: #b3e5fc;
  }

  .toast-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .toast-machine {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.7;
  }

  .toast-message {
    line-height: 1.3;
  }

  .toast-dismiss {
    background: transparent;
    border: none;
    color: inherit;
    opacity: 0.6;
    font-size: 1rem;
    cursor: pointer;
    padding: 0 2px;
    line-height: 1;
    flex-shrink: 0;
  }

  .toast-dismiss:hover {
    opacity: 1;
  }

  @media (max-width: 480px) {
    .toast-container {
      left: 8px;
      right: 8px;
      max-width: none;
    }

    .toast-dismiss {
      padding: 4px 8px;
    }
  }
</style>
