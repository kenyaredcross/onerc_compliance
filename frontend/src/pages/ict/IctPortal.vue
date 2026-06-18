<template>
  <div class="ict-portal">
    <header class="ict-topbar">
      <router-link to="/ict-help" class="ict-brand">
        <span class="ict-mark">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7z" />
          </svg>
        </span>
        <span>ICT Help <span class="ict-brand-sub">· OneRC</span></span>
      </router-link>
      <div class="ict-topbar-right">
        <a href="/compliance" class="ict-back ict-topbar-link">Compliance</a>
        <div class="ict-avatar" :title="display">{{ initial }}</div>
      </div>
    </header>

    <main>
      <router-view v-slot="{ Component }">
        <transition name="ict-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <div class="ict-toasts" aria-live="polite">
      <transition-group name="ict-toast">
        <button
          v-for="t in toasts"
          :key="t.id"
          class="ict-toast"
          :class="`ict-toast-${t.type}`"
          @click="dismiss(t.id)"
        >
          {{ t.message }}
        </button>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { useIctUser } from '@/composables/useIctUser.js'
import { useToast } from '@/composables/useToast.js'
const { initial, display } = useIctUser()
const { toasts, dismiss } = useToast()
</script>

<style>
/* ── ICT Help portal design system (namespaced under .ict-portal) ───────── */
.ict-portal {
  --paper: #faf8f5;
  --paper-2: #ffffff;
  --ink: #1b1a18;
  --muted: #6f6a63;
  --line: #ece7df;
  --line-2: #e2d9cc;
  --accent: #e2231a;
  --accent-ink: #b81b14;
  --accent-soft: #fbedeb;
  --shadow: 0 1px 2px rgba(20, 18, 15, 0.04), 0 10px 26px -14px rgba(20, 18, 15, 0.16);
  --shadow-hover: 0 2px 5px rgba(20, 18, 15, 0.06), 0 22px 48px -18px rgba(20, 18, 15, 0.26);
  --font-display: 'Fraunces', Georgia, 'Times New Roman', serif;
  --font-body: 'Hanken Grotesk', system-ui, -apple-system, sans-serif;

  min-height: 100vh;
  background: radial-gradient(120% 60% at 50% -8%, #ffffff 0%, var(--paper) 58%);
  color: var(--ink);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
.ict-portal * { box-sizing: border-box; }

.ict-topbar {
  height: 60px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 clamp(16px, 4vw, 40px); border-bottom: 1px solid var(--line);
  position: sticky; top: 0; z-index: 20;
  background: color-mix(in srgb, var(--paper) 82%, transparent);
  backdrop-filter: saturate(1.2) blur(10px);
}
.ict-brand { display: flex; align-items: center; gap: 10px; font-weight: 700; letter-spacing: -0.01em; color: var(--ink); text-decoration: none; }
.ict-brand-sub { color: var(--muted); font-weight: 500; }
.ict-mark { width: 28px; height: 28px; border-radius: 8px; background: var(--accent); color: #fff; display: grid; place-items: center; box-shadow: 0 3px 10px -2px rgba(226, 35, 26, 0.55); }
.ict-topbar-right { display: flex; align-items: center; gap: 16px; }
.ict-topbar-link { font-size: 13px; }
.ict-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--ink); color: #fff; display: grid; place-items: center; font-weight: 700; font-size: 13px; }

.ict-shell { max-width: 980px; margin: 0 auto; padding: clamp(30px, 6vw, 76px) clamp(16px, 4vw, 40px) 88px; }
.ict-shell-narrow { max-width: 720px; }

.ict-display { font-family: var(--font-display); font-weight: 600; letter-spacing: -0.02em; line-height: 1.03; }
.ict-eyebrow { font-size: 12px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent-ink); }
.ict-muted { color: var(--muted); }
.ict-accent { color: var(--accent); }

.ict-card { background: var(--paper-2); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); transition: transform 0.22s cubic-bezier(0.2, 0.7, 0.2, 1), box-shadow 0.22s, border-color 0.22s; }
a.ict-card { text-decoration: none; color: inherit; display: block; }
.ict-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-hover); border-color: var(--line-2); }

.ict-bigcard { padding: 28px; display: flex; flex-direction: column; min-height: 224px; }
.ict-bigcard:hover { border-color: color-mix(in srgb, var(--accent) 32%, var(--line)); }
.ict-bigcard:hover .ict-iconbox { background: var(--accent); color: #fff; }
.ict-bigcard:hover .ict-arrow { gap: 10px; color: var(--accent); }
.ict-iconbox { width: 52px; height: 52px; border-radius: 14px; display: grid; place-items: center; background: var(--accent-soft); color: var(--accent); transition: background 0.22s, color 0.22s; }
.ict-arrow { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; font-size: 14px; color: var(--ink); transition: gap 0.2s ease, color 0.2s; }

.ict-btn { font: inherit; font-weight: 600; font-size: 14px; border-radius: 11px; padding: 11px 18px; cursor: pointer; border: 1px solid transparent; transition: transform 0.15s, background 0.15s, border-color 0.15s, color 0.15s; display: inline-flex; align-items: center; gap: 8px; justify-content: center; }
.ict-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.ict-btn-primary { background: var(--ink); color: #fff; }
.ict-btn-primary:hover:not(:disabled) { background: #000; transform: translateY(-1px); }
.ict-btn-accent { background: var(--accent); color: #fff; }
.ict-btn-accent:hover:not(:disabled) { background: var(--accent-ink); transform: translateY(-1px); }
.ict-btn-ghost { background: transparent; border-color: var(--line); color: var(--ink); }
.ict-btn-ghost:hover:not(:disabled) { background: #f5f1ea; }

.ict-input, .ict-textarea { width: 100%; font: inherit; font-size: 15px; padding: 12px 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--paper-2); color: var(--ink); transition: border-color 0.15s, box-shadow 0.15s; }
.ict-input::placeholder, .ict-textarea::placeholder { color: #a8a299; }
.ict-input:focus, .ict-textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }
.ict-textarea { resize: vertical; min-height: 110px; }
.ict-label { font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 7px; display: block; }

.ict-search { width: 100%; font: inherit; font-size: 15px; padding: 13px 16px 13px 44px; border: 1px solid var(--line); border-radius: 14px; background: var(--paper-2) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' stroke='%236f6a63' stroke-width='2' viewBox='0 0 24 24'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E") no-repeat 15px center; box-shadow: var(--shadow); transition: border-color 0.15s, box-shadow 0.15s; }
.ict-search:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }

.ict-chip { font: inherit; font-size: 13px; font-weight: 500; padding: 7px 14px; border-radius: 999px; border: 1px solid var(--line); background: var(--paper-2); color: var(--ink); cursor: pointer; transition: all 0.15s; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
.ict-chip:hover { border-color: var(--line-2); background: #f5f1ea; }

.ict-badge { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; display: inline-flex; align-items: center; gap: 5px; border: 1px solid transparent; }
.ict-badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.ict-badge-new, .ict-badge-draft { background: #f1ece3; color: #6f6a63; }
.ict-badge-progress, .ict-badge-pending { background: #fff4e2; color: #b06b00; }
.ict-badge-open, .ict-badge-assigned, .ict-badge-fulfilment { background: #e8f0fe; color: #1a56b0; }
.ict-badge-done, .ict-badge-resolved, .ict-badge-fulfilled, .ict-badge-closed, .ict-badge-approved { background: #e6f4ea; color: #1d7a3e; }
.ict-badge-breach, .ict-badge-rejected, .ict-badge-cancelled { background: var(--accent-soft); color: var(--accent-ink); }

.ict-seg { display: inline-flex; background: #f1ece3; border-radius: 13px; padding: 4px; gap: 3px; }
.ict-seg button { border: none; background: transparent; font: inherit; font-weight: 600; font-size: 14px; padding: 9px 18px; border-radius: 10px; cursor: pointer; color: var(--muted); transition: all 0.15s; }
.ict-seg button.active { background: #fff; color: var(--ink); box-shadow: 0 1px 3px rgba(20, 18, 15, 0.1); }

.ict-back { display: inline-flex; align-items: center; gap: 7px; color: var(--muted); font-weight: 600; font-size: 14px; text-decoration: none; transition: color 0.15s; }
.ict-back:hover { color: var(--ink); }

.ict-skel { background: linear-gradient(90deg, #f0ebe3 25%, #f7f3ec 37%, #f0ebe3 63%); background-size: 400% 100%; animation: ictShimmer 1.4s ease infinite; border-radius: 12px; }

.ict-toasts { position: fixed; top: 16px; right: 16px; z-index: 80; display: flex; flex-direction: column; gap: 10px; max-width: min(92vw, 380px); }
.ict-toast { font: inherit; text-align: left; font-size: 14px; font-weight: 500; padding: 13px 16px; border-radius: 13px; border: 1px solid var(--line); background: var(--paper-2); color: var(--ink); box-shadow: var(--shadow-hover); cursor: pointer; display: flex; gap: 10px; align-items: center; }
.ict-toast::before { content: ''; width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; background: var(--muted); }
.ict-toast-success::before { background: #1d7a3e; }
.ict-toast-error::before { background: var(--accent); }
.ict-toast-info::before { background: #1a56b0; }
.ict-toast-enter-active, .ict-toast-leave-active { transition: all 0.28s cubic-bezier(0.2, 0.7, 0.2, 1); }
.ict-toast-enter-from { opacity: 0; transform: translateX(16px); }
.ict-toast-leave-to { opacity: 0; transform: translateX(16px); }

@keyframes ictRise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
@keyframes ictShimmer { 0% { background-position: 100% 0; } 100% { background-position: 0 0; } }
.ict-rise { animation: ictRise 0.6s cubic-bezier(0.2, 0.7, 0.2, 1) both; }

.ict-fade-enter-active, .ict-fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.ict-fade-enter-from { opacity: 0; transform: translateY(6px); }
.ict-fade-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .ict-rise, .ict-skel { animation: none; }
  .ict-card { transition: none; }
}
</style>
