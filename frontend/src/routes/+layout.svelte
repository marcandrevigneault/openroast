<script lang="ts">
  import favicon from "$lib/assets/favicon.svg";

  let { children } = $props();
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <title>OpenRoast</title>
</svelte:head>

<div class="app">
  <header class="app-header">
    <h1 class="logo">OpenRoast</h1>
  </header>
  <main class="app-main">
    {@render children()}
  </main>
</div>

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

  /* Prevent iOS zoom on input focus */
  :global(input, select, textarea) {
    font-size: 16px;
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
    padding: 10px 20px;
    background: #12122a;
    border-bottom: 1px solid #2a2a4a;
  }

  .logo {
    font-size: 1.1rem;
    font-weight: 700;
    color: #4fc3f7;
    margin: 0;
    letter-spacing: 0.05em;
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
