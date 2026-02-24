<script lang="ts">
  import favicon from "$lib/assets/favicon.png";
  import AppMenu from "$lib/components/AppMenu.svelte";

  let { children } = $props();
  let menuOpen = $state(false);
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
  </header>
  <main class="app-main">
    {@render children()}
  </main>
</div>

<AppMenu open={menuOpen} onclose={() => (menuOpen = false)} />

<style>
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background: #0a0a1a;
    color: #e0e0e0;
    font-family:
      -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
    -webkit-text-size-adjust: 100%;
    overflow-x: hidden;
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
    background: #12122a;
    border-bottom: 1px solid #2a2a4a;
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
    background: #999;
    border-radius: 1px;
    transition: background 0.15s;
  }

  .btn-menu:hover .hamburger-line {
    background: #4fc3f7;
  }

  .logo {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f5f0e8;
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
