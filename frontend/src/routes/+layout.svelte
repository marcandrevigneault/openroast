<script lang="ts">
  import favicon from "$lib/assets/favicon.png";
  import AppMenu from "$lib/components/AppMenu.svelte";
  import ThemeToggle from "$lib/components/ThemeToggle.svelte";
  import { theme } from "$lib/stores/theme.svelte";

  let { children } = $props();
  let menuOpen = $state(false);

  // Apply persisted theme on mount so SSR-rendered HTML matches.
  $effect(() => {
    theme.init();
  });
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <title>OpenRoast</title>
</svelte:head>

<div class="app">
  <header class="app-header">
    <button
      class="btn-menu"
      onclick={() => (menuOpen = true)}
      aria-label="Open menu"
    >
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
    </button>
    <h1 class="logo">OpenRoast</h1>
    <img class="logo-icon" src={favicon} alt="" />
    <div class="header-spacer"></div>
    <ThemeToggle />
  </header>
  <main class="app-main">
    {@render children()}
  </main>
</div>

<AppMenu open={menuOpen} onclose={() => (menuOpen = false)} />

<style>
  /* Theme tokens.  The default values here are the dark theme; the
     [data-theme="light"] block overrides them.  Components that opt in
     by reading var(--token) get themed automatically; legacy components
     with hardcoded colors keep the dark palette until refactored. */
  :global(:root) {
    --bg: #0a0a1a;
    --bg-elevated: #12122a;
    --surface: #1a1a2e;
    --surface-hover: rgba(255, 255, 255, 0.06);
    --border: #2a2a4a;
    --text: #e0e0e0;
    --text-muted: #999;
    --text-strong: #f5f0e8;
    --accent: #4fc3f7;
    --accent-soft: rgba(79, 195, 247, 0.12);
    --overlay: rgba(0, 0, 0, 0.6);
    color-scheme: dark;
  }

  :global(html[data-theme="light"]) {
    --bg: #f5f5f7;
    --bg-elevated: #ffffff;
    --surface: #ffffff;
    --surface-hover: rgba(0, 0, 0, 0.05);
    --border: #d8d8e0;
    --text: #1a1a2e;
    --text-muted: #5a5a6a;
    --text-strong: #0a0a1a;
    --accent: #0277bd;
    --accent-soft: rgba(2, 119, 189, 0.12);
    --overlay: rgba(0, 0, 0, 0.4);
    color-scheme: light;
  }

  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family:
      -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
    -webkit-text-size-adjust: 100%;
    overflow-x: hidden;
    transition:
      background 0.18s ease,
      color 0.18s ease;
  }

  /* Prevent iOS zoom on text input focus (16px minimum prevents auto-zoom).
     Only target text-entry elements — not range sliders or styled inputs. */
  :global(
    input[type="text"],
    input[type="number"],
    input[type="email"],
    input[type="password"],
    input[type="search"],
    input[type="tel"],
    input[type="url"],
    input:not([type]),
    select,
    textarea
  ) {
    font-size: max(16px, 1em);
  }

  .app {
    min-height: 100vh;
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
  }

  .app-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 20px;
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border);
  }

  .header-spacer {
    flex: 1;
  }

  .btn-menu {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 4px;
  }

  .hamburger-line {
    display: block;
    width: 20px;
    height: 2px;
    background: var(--text-muted);
    border-radius: 1px;
    transition: background 0.15s;
  }

  .btn-menu:hover .hamburger-line {
    background: var(--accent);
  }

  .logo {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-strong);
    margin: 0;
    letter-spacing: 0.05em;
  }

  .logo-icon {
    width: 24px;
    height: 24px;
    object-fit: contain;
  }

  .app-main {
    flex: 1;
    padding: 20px;
  }

  @media (max-width: 768px) {
    .app-header {
      padding: 8px 12px;
    }

    .app-main {
      padding: 8px;
    }
  }
</style>
