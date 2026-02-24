<script lang="ts">
  import { page } from "$app/state";
  import { resolve } from "$app/paths";

  interface Props {
    open: boolean;
    onclose?: () => void;
  }

  let { open, onclose }: Props = $props();

  const links: {
    href: "/" | "/profiles" | "/control-profiles";
    label: string;
  }[] = [
    { href: "/", label: "Dashboard" },
    { href: "/profiles", label: "Profiles" },
    { href: "/control-profiles", label: "Control Profiles" },
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
      <span class="drawer-title">OpenRoast</span>
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
  </nav>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 199;
  }

  .drawer {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 260px;
    max-width: 80vw;
    background: #12122a;
    border-right: 1px solid #2a2a4a;
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
    border-bottom: 1px solid #2a2a4a;
  }

  .drawer-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #4fc3f7;
    letter-spacing: 0.05em;
  }

  .btn-close {
    background: transparent;
    border: none;
    color: #666;
    font-size: 1.4rem;
    cursor: pointer;
    padding: 2px 6px;
    line-height: 1;
  }

  .btn-close:hover {
    color: #e0e0e0;
  }

  .nav-list {
    list-style: none;
    margin: 0;
    padding: 8px 0;
  }

  .nav-link {
    display: block;
    padding: 12px 20px;
    color: #b0b0b0;
    text-decoration: none;
    font-size: 0.95rem;
    font-weight: 500;
    transition:
      background 0.15s,
      color 0.15s;
  }

  .nav-link:hover {
    background: rgba(79, 195, 247, 0.08);
    color: #e0e0e0;
  }

  .nav-link.active {
    color: #4fc3f7;
    background: rgba(79, 195, 247, 0.12);
    border-left: 3px solid #4fc3f7;
  }
</style>
