<script lang="ts">
  import { page } from "$app/state";
  import { resolve } from "$app/paths";
  import favicon from "$lib/assets/favicon.png";
  import { fetchVersion } from "$lib/utils/api";

  interface Props {
    open: boolean;
    onclose?: () => void;
  }

  let { open, onclose }: Props = $props();
  let version: string = $state("...");

  $effect(() => {
    fetchVersion().then((v) => {
      version = v;
    });
  });

  const links: {
    href: "/" | "/profiles" | "/control-profiles" | "/simulator";
    label: string;
  }[] = [
    { href: "/", label: "Dashboard" },
    { href: "/profiles", label: "Profiles" },
    { href: "/control-profiles", label: "Control Profiles" },
    { href: "/simulator", label: "Simulator" },
  ];

  function handleNav() {
    onclose?.();
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="overlay" onkeydown={() => {}} onclick={onclose}></div>
  <nav class="drawer" aria-label="Main navigation">
    <div class="drawer-header">
      <span class="drawer-brand">
        <span class="drawer-title">OpenRoast</span>
        <img class="drawer-logo" src={favicon} alt="" />
      </span>
      <button class="btn-close" onclick={onclose} aria-label="Close menu"
        >&times;</button
      >
    </div>
    <ul class="nav-list">
      {#each links as link (link.href)}
        <li>
          <a
            href={resolve(link.href)}
            class="nav-link"
            class:active={page.url.pathname === link.href}
            onclick={handleNav}
          >
            {link.label}
          </a>
        </li>
      {/each}
    </ul>
    <div class="drawer-footer">
      <span class="version-label">v{version}</span>
    </div>
  </nav>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: var(--overlay, rgba(0, 0, 0, 0.6));
    z-index: 199;
  }

  .drawer {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 260px;
    max-width: 80vw;
    background: var(--bg-elevated, var(--bg-elevated));
    border-right: 1px solid var(--border, var(--border));
    z-index: 200;
    display: flex;
    flex-direction: column;
    animation: slide-in 0.2s ease-out;
  }

  @keyframes slide-in {
    from {
      transform: translateX(-100%);
    }
    to {
      transform: translateX(0);
    }
  }

  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border, var(--border));
  }

  .drawer-brand {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .drawer-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-strong, var(--text-strong));
    letter-spacing: 0.05em;
  }

  .drawer-logo {
    width: 24px;
    height: 24px;
    object-fit: contain;
  }

  .btn-close {
    background: transparent;
    border: none;
    color: var(--text-muted, var(--text-faint));
    font-size: 1.4rem;
    cursor: pointer;
    padding: 2px 6px;
    line-height: 1;
  }

  .btn-close:hover {
    color: var(--text, var(--text));
  }

  .nav-list {
    list-style: none;
    margin: 0;
    padding: 8px 0;
  }

  .nav-link {
    display: block;
    padding: 12px 20px;
    color: var(--text-muted, var(--text-muted));
    text-decoration: none;
    font-size: 0.95rem;
    font-weight: 500;
    transition:
      background 0.15s,
      color 0.15s;
  }

  .nav-link:hover {
    background: var(--surface-hover, rgba(79, 195, 247, 0.08));
    color: var(--text, var(--text));
  }

  .nav-link.active {
    color: var(--accent, var(--accent));
    background: var(--accent-soft, rgba(79, 195, 247, 0.12));
    border-left: 3px solid var(--accent, var(--accent));
  }

  .drawer-footer {
    margin-top: auto;
    padding: 12px 20px;
    border-top: 1px solid var(--border, var(--border));
  }

  .version-label {
    font-size: 0.75rem;
    color: var(--text-muted, var(--text-faint));
    letter-spacing: 0.03em;
  }
</style>
