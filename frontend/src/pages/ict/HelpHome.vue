<template>
  <div class="ict-shell">
    <div class="ict-hero">
      <p class="ict-eyebrow ict-rise" style="animation-delay: 0ms">ICT Service Desk</p>
      <h1 class="ict-display ict-rise" style="animation-delay: 60ms; font-size: clamp(36px, 6.4vw, 62px); margin: 16px 0 0;">
        How can we help<br />you, <span class="ict-accent">{{ firstName }}</span>?
      </h1>
      <p class="ict-rise ict-muted" style="animation-delay: 120ms; font-size: 17px; margin-top: 18px; line-height: 1.5;">
        Request what you need from the catalogue, or report something that's broken — we'll route it to
        the right team and keep you posted.
      </p>
    </div>

    <div class="ict-home-grid">
      <router-link to="/ict-help/resources" class="ict-card ict-bigcard ict-rise" style="animation-delay: 180ms">
        <div class="ict-iconbox">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
            <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
          </svg>
        </div>
        <h3 class="ict-display" style="font-size: 25px; margin: 18px 0 0;">Resource Access</h3>
        <p class="ict-muted" style="margin: 9px 0 0; font-size: 15px; line-height: 1.5; flex: 1;">
          Hardware, software, accounts and system access — pick from the catalogue and we'll set you up.
        </p>
        <span class="ict-arrow" style="margin-top: 18px;">
          Browse catalogue
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
        </span>
      </router-link>

      <router-link to="/ict-help/support" class="ict-card ict-bigcard ict-rise" style="animation-delay: 240ms">
        <div class="ict-iconbox">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 9v4M12 17h.01" />
            <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
          </svg>
        </div>
        <h3 class="ict-display" style="font-size: 25px; margin: 18px 0 0;">Report an Issue</h3>
        <p class="ict-muted" style="margin: 9px 0 0; font-size: 15px; line-height: 1.5; flex: 1;">
          Something not working? Log a ticket in seconds and track it through to resolution.
        </p>
        <span class="ict-arrow" style="margin-top: 18px;">
          Report or view tickets
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
        </span>
      </router-link>
    </div>

    <div class="ict-rise" style="animation-delay: 320ms; text-align: center; margin-top: 34px;">
      <router-link to="/ict-help/support" class="ict-back">Track my existing tickets →</router-link>
    </div>
  </div>
</template>

<script setup>
import { useIctUser } from '@/composables/useIctUser.js'
const { firstName } = useIctUser()
</script>

<style scoped>
.ict-hero { text-align: center; max-width: 640px; margin: 0 auto; }
.ict-home-grid { display: grid; grid-template-columns: 1fr; gap: 18px; margin: clamp(36px, 6vw, 56px) auto 0; max-width: 760px; }
@media (min-width: 640px) { .ict-home-grid { grid-template-columns: 1fr 1fr; } }
</style>
