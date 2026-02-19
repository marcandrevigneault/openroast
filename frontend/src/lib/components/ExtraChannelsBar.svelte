<script lang="ts">
  import type { ExtraChannelConfig } from "$lib/stores/machine";

  interface Props {
    channels: ExtraChannelConfig[];
    values: Record<string, number>;
  }

  let { channels, values }: Props = $props();
</script>

{#if channels.length > 0}
  <div class="extra-channels-bar">
    {#each channels as ch (ch.name)}
      <div class="channel-badge">
        <span class="channel-name">{ch.name}</span>
        <span class="channel-value">
          {values[ch.name] !== undefined ? values[ch.name].toFixed(1) : "---"}
        </span>
      </div>
    {/each}
  </div>
{/if}

<style>
  .extra-channels-bar {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .channel-badge {
    display: flex;
    align-items: baseline;
    gap: 4px;
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    padding: 3px 8px;
  }

  .channel-name {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
  }

  .channel-value {
    font-size: 0.8rem;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-weight: 600;
    color: #a5d6a7;
  }
</style>
