<script lang="ts">
  import { onMount } from "svelte";
  import {
    listProfiles,
    getProfile,
    deleteProfile,
    getProfileImageUrl,
    saveSchedule,
    type ProfileSummary,
    type FullProfile,
  } from "$lib/utils/api";
  import { addToast } from "$lib/stores/toast";
  import { formatTime } from "$lib/stores/machine";
  import ToastContainer from "$lib/components/ToastContainer.svelte";

  let profiles = $state<ProfileSummary[]>([]);
  let loading = $state(true);
  let selectedProfile = $state<FullProfile | null>(null);
  let loadingDetail = $state(false);
  let confirmDeleteId = $state<string | null>(null);
  let creatingControlProfile = $state(false);

  async function load() {
    loading = true;
    try {
      profiles = await listProfiles();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load profiles";
      addToast(msg, "error");
    } finally {
      loading = false;
    }
  }

  async function viewProfile(id: string) {
    loadingDetail = true;
    try {
      selectedProfile = await getProfile(id);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load profile";
      addToast(msg, "error");
    } finally {
      loadingDetail = false;
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteProfile(id);
      profiles = profiles.filter((p) => p.id !== id);
      if (selectedProfile?.id === id) selectedProfile = null;
      confirmDeleteId = null;
      addToast("Profile deleted", "info");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to delete profile";
      addToast(msg, "error");
    }
  }

  async function createControlProfile() {
    if (!selectedProfile) return;
    const controls = selectedProfile.controls;
    if (Object.keys(controls).length === 0) return;

    creatingControlProfile = true;
    try {
      // Group control points by timestamp into steps
      const byTimestamp: Record<number, { channel: string; value: number }[]> =
        {};
      for (const [channel, points] of Object.entries(controls)) {
        for (const [timestamp_ms, value] of points) {
          const existing = byTimestamp[timestamp_ms] ?? [];
          existing.push({ channel, value });
          byTimestamp[timestamp_ms] = existing;
        }
      }

      const steps = Object.entries(byTimestamp)
        .map(([tsStr, actions]) => ({ ts: Number(tsStr), actions }))
        .sort((a, b) => a.ts - b.ts)
        .map(({ ts, actions }, i) => ({
          id: `imported-${i}`,
          trigger: { type: "time" as const, timestamp_ms: ts },
          actions,
          fired: false,
          enabled: true,
        }));

      await saveSchedule({
        name: `${selectedProfile.name} control profile`,
        machine_name: selectedProfile.machine,
        steps,
        source_profile_name: selectedProfile.name,
      });
      addToast("Control profile created", "info");
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Failed to create control profile";
      addToast(msg, "error");
    } finally {
      creatingControlProfile = false;
    }
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

<div class="profiles-page">
  <h2 class="page-title">Profiles</h2>
  <p class="page-desc">
    Saved roast records — what happened during each roast.
  </p>

  {#if loading}
    <p class="loading">Loading profiles...</p>
  {:else if profiles.length === 0}
    <div class="empty-state">
      <p>No saved profiles yet.</p>
      <p class="hint">Complete a roast recording and save it to see it here.</p>
    </div>
  {:else}
    <div class="profiles-list">
      {#each profiles as p (p.id)}
        <div class="profile-card" class:selected={selectedProfile?.id === p.id}>
          <button class="card-body" onclick={() => viewProfile(p.id)}>
            <div class="card-title">{p.name}</div>
            <div class="card-meta">
              <span>{p.machine}</span>
              {#if p.bean_name}
                <span class="sep">·</span>
                <span>{p.bean_name}</span>
              {/if}
            </div>
            <div class="card-meta">
              <span>{formatDate(p.created_at)}</span>
              <span class="sep">·</span>
              <span>{p.data_points} data points</span>
            </div>
          </button>
          <div class="card-actions">
            {#if confirmDeleteId === p.id}
              <button
                class="btn-confirm-delete"
                onclick={() => handleDelete(p.id)}>Confirm</button
              >
              <button
                class="btn-cancel-delete"
                onclick={() => (confirmDeleteId = null)}>Cancel</button
              >
            {:else}
              <button
                class="btn-delete"
                onclick={() => (confirmDeleteId = p.id)}
                title="Delete profile">&#128465;</button
              >
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if selectedProfile}
    <div class="detail-panel">
      <div class="detail-header">
        <h3>{selectedProfile.name}</h3>
        <button
          class="btn-close-detail"
          onclick={() => (selectedProfile = null)}>&times;</button
        >
      </div>

      <div class="detail-meta">
        <div><strong>Machine:</strong> {selectedProfile.machine}</div>
        <div>
          <strong>Date:</strong>
          {formatDate(selectedProfile.created_at)}
        </div>
        {#if selectedProfile.bean_name}
          <div><strong>Bean:</strong> {selectedProfile.bean_name}</div>
        {/if}
        {#if selectedProfile.schedule_name}
          <div>
            <strong>Control Profile:</strong>
            {selectedProfile.schedule_name}
          </div>
        {/if}
      </div>

      {#if profiles.find((p) => p.id === selectedProfile?.id)?.has_image}
        <div class="detail-image">
          <img
            src={getProfileImageUrl(selectedProfile.id)}
            alt="Roast chart for {selectedProfile.name}"
          />
        </div>
      {/if}

      {#if selectedProfile.events.length > 0}
        <div class="detail-section">
          <h4>Events</h4>
          <div class="events-list">
            {#each selectedProfile.events as evt, i (i)}
              <div class="event-item">
                <span class="event-type">{evt.event_type}</span>
                <span class="event-time">{formatTime(evt.timestamp_ms)}</span>
                {#if evt.auto_detected}
                  <span class="event-auto">auto</span>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if Object.keys(selectedProfile.controls).length > 0}
        <div class="detail-section">
          <div class="section-header">
            <h4>Controls</h4>
            <button
              class="btn-create-cp"
              onclick={createControlProfile}
              disabled={creatingControlProfile}
            >
              {creatingControlProfile
                ? "Creating..."
                : "Create Control Profile"}
            </button>
          </div>
          {#each Object.entries(selectedProfile.controls) as [channel, points] (channel)}
            <div class="control-channel">
              <span class="channel-name">{channel}</span>
              <div class="control-steps">
                {#each points as [ts, val], i (i)}
                  <span class="step">{formatTime(ts)}: {val}</span>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      {/if}

      <div class="detail-section">
        <h4>Summary</h4>
        <div>{selectedProfile.temperatures.length} data points</div>
        {#if selectedProfile.temperatures.length > 0}
          {@const last =
            selectedProfile.temperatures[
              selectedProfile.temperatures.length - 1
            ]}
          <div>Duration: {formatTime(last.timestamp_ms)}</div>
        {/if}
      </div>
    </div>
  {/if}

  {#if loadingDetail}
    <div class="loading-overlay">Loading...</div>
  {/if}
</div>

<style>
  .profiles-page {
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

  .profiles-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .profile-card {
    display: flex;
    align-items: center;
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    overflow: hidden;
    transition: border-color 0.15s;
  }

  .profile-card:hover {
    border-color: #3a3a5a;
  }

  .profile-card.selected {
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
  }

  .detail-header h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #e0e0e0;
  }

  .btn-close-detail {
    background: transparent;
    border: none;
    color: #666;
    font-size: 1.4rem;
    cursor: pointer;
    padding: 2px 6px;
  }

  .btn-close-detail:hover {
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

  .detail-image {
    margin-bottom: 16px;
  }

  .detail-image img {
    width: 100%;
    border-radius: 6px;
    border: 1px solid #2a2a4a;
  }

  .detail-section {
    margin-bottom: 16px;
  }

  .detail-section h4 {
    font-size: 0.9rem;
    color: #b0b0b0;
    margin: 0 0 8px;
    font-weight: 600;
  }

  .events-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .event-item {
    display: flex;
    gap: 6px;
    align-items: center;
    background: #1a1a3a;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 0.8rem;
  }

  .event-type {
    color: #4fc3f7;
    font-weight: 600;
  }

  .event-time {
    color: #999;
  }

  .event-auto {
    color: #66bb6a;
    font-size: 0.7rem;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .section-header h4 {
    margin: 0;
  }

  .btn-create-cp {
    background: rgba(79, 195, 247, 0.1);
    border: 1px solid #4fc3f7;
    color: #4fc3f7;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.75rem;
    cursor: pointer;
  }

  .btn-create-cp:hover {
    background: rgba(79, 195, 247, 0.2);
  }

  .btn-create-cp:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .control-channel {
    margin-bottom: 8px;
  }

  .channel-name {
    font-weight: 600;
    color: #e6c229;
    font-size: 0.85rem;
  }

  .control-steps {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
  }

  .step {
    background: #1a1a3a;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    color: #bbb;
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
  }
</style>
