<template>
  <div class="ict-shell ict-shell-narrow">
    <router-link to="/ict-help" class="ict-back">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
      Back
    </router-link>

    <header style="margin-top: 20px;">
      <p class="ict-eyebrow">Support</p>
      <h1 class="ict-display" style="font-size: clamp(30px, 5vw, 44px); margin: 12px 0 0;">Report &amp; track</h1>
    </header>

    <div class="ict-seg" style="margin-top: 22px;">
      <button :class="{ active: tab === 'report' }" @click="tab = 'report'">Report an issue</button>
      <button :class="{ active: tab === 'tickets' }" @click="switchToTickets">My tickets</button>
    </div>

    <!-- Report -->
    <div v-if="tab === 'report'" class="ict-card ict-rise" style="margin-top: 22px; padding: 26px;">
      <div>
        <label class="ict-label">What's going wrong?</label>
        <input v-model="form.title" class="ict-input" placeholder="e.g. Cannot connect to the VPN" @keyup.enter="focusDesc" />
      </div>
      <div style="margin-top: 16px;">
        <label class="ict-label">Tell us more</label>
        <textarea ref="descEl" v-model="form.description" class="ict-textarea" placeholder="When did it start, what have you tried, any error messages…"></textarea>
      </div>
      <div v-if="urgencies.length" style="margin-top: 16px;">
        <label class="ict-label">How urgent is it?</label>
        <div class="ict-seg">
          <button v-for="u in urgencies" :key="u.name" type="button" :class="{ active: form.urgency === u.name }" @click="form.urgency = u.name">
            {{ u.urgency_name || u.name }}
          </button>
        </div>
      </div>
      <div style="display: flex; justify-content: flex-end; margin-top: 22px;">
        <button class="ict-btn ict-btn-accent" :disabled="!canSubmit || submitting" @click="submit">
          {{ submitting ? 'Logging…' : 'Submit ticket' }}
        </button>
      </div>
    </div>

    <!-- Tickets -->
    <div v-else style="margin-top: 22px;">
      <div v-if="loadingTickets" style="display: grid; gap: 12px;">
        <div v-for="n in 4" :key="n" class="ict-skel" style="height: 70px;"></div>
      </div>
      <div v-else-if="!tickets.length" class="ict-card" style="padding: 48px; text-align: center;">
        <p class="ict-muted">You haven't logged anything yet.</p>
        <button class="ict-btn ict-btn-ghost" style="margin-top: 14px;" @click="tab = 'report'">Report an issue</button>
      </div>
      <div v-else style="display: flex; flex-direction: column; gap: 12px;">
        <div v-for="(t, i) in tickets" :key="t.type + t.name" class="ict-card ict-ticket ict-rise" :style="{ animationDelay: i * 45 + 'ms' }">
          <span class="ict-ticket-icon" :data-type="t.type">{{ t.type === 'Incident' ? '!' : '+' }}</span>
          <span style="flex: 1; min-width: 0;">
            <span style="display: flex; align-items: center; gap: 9px; flex-wrap: wrap;">
              <span class="ict-ticket-subject">{{ t.subject }}</span>
              <span class="ict-badge" :class="badgeClass(t.status)">{{ t.status }}</span>
            </span>
            <span class="ict-muted" style="display: block; font-size: 13px; margin: 4px 0 0;">
              {{ t.name }} · {{ t.type }}<template v-if="t.priority"> · {{ t.priority }}</template> · {{ fmt(t.creation) }}
            </span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useApi } from '@/composables/useApi.js'
import { useToast } from '@/composables/useToast.js'

const PFX = 'onerc_compliance.onerc_incident_management.portal.'
const api = useApi()
const toast = useToast()

const tab = ref('report')
const urgencies = ref([])
const form = reactive({ title: '', description: '', urgency: 'Medium' })
const submitting = ref(false)
const descEl = ref(null)

const tickets = ref([])
const loadingTickets = ref(false)
let ticketsLoaded = false

const canSubmit = computed(() => form.title.trim().length > 2)

onMounted(async () => {
  try {
    urgencies.value = await api.call(PFX + 'get_urgency_options')
    if (urgencies.value.length && !urgencies.value.find((u) => u.name === form.urgency)) {
      form.urgency = urgencies.value[Math.floor(urgencies.value.length / 2)].name
    }
  } catch {
    /* urgency picker is optional */
  }
})

function focusDesc() {
  nextTick(() => descEl.value?.focus())
}

async function loadTickets() {
  loadingTickets.value = true
  try {
    tickets.value = await api.call(PFX + 'get_my_tickets')
  } catch (e) {
    toast.error(e.message || 'Could not load your tickets.')
  } finally {
    loadingTickets.value = false
    ticketsLoaded = true
  }
}
function switchToTickets() {
  tab.value = 'tickets'
  if (!ticketsLoaded) loadTickets()
}

async function submit() {
  submitting.value = true
  try {
    const res = await api.call(PFX + 'submit_incident', {
      title: form.title,
      description: form.description,
      urgency: form.urgency,
    })
    toast.success(`Ticket ${res.name} logged — priority ${res.priority || '—'}.`)
    form.title = ''
    form.description = ''
    ticketsLoaded = false
    switchToTickets()
  } catch (e) {
    toast.error(e.message || 'Could not log your ticket.')
  } finally {
    submitting.value = false
  }
}

function badgeClass(status) {
  const s = (status || '').toLowerCase().replace(/\s+/g, '-')
  const map = {
    new: 'ict-badge-new', draft: 'ict-badge-draft', assigned: 'ict-badge-assigned',
    'in-progress': 'ict-badge-progress', pending: 'ict-badge-pending',
    'pending-hod': 'ict-badge-pending', 'pending-ict': 'ict-badge-pending',
    approved: 'ict-badge-approved', 'in-fulfilment': 'ict-badge-fulfilment',
    resolved: 'ict-badge-resolved', fulfilled: 'ict-badge-fulfilled',
    closed: 'ict-badge-closed', cancelled: 'ict-badge-cancelled', rejected: 'ict-badge-rejected',
  }
  return map[s] || 'ict-badge-new'
}
function fmt(dt) {
  if (!dt) return ''
  const d = new Date(String(dt).replace(' ', 'T'))
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}
</script>

<style scoped>
.ict-ticket { display: flex; align-items: center; gap: 14px; padding: 15px 18px; }
.ict-ticket-icon { width: 38px; height: 38px; border-radius: 10px; display: grid; place-items: center; font-weight: 800; font-size: 17px; flex-shrink: 0; font-family: var(--font-display); }
.ict-ticket-icon[data-type='Incident'] { background: var(--accent-soft); color: var(--accent); }
.ict-ticket-icon[data-type='Service Request'] { background: #e8f0fe; color: #1a56b0; }
.ict-ticket-subject { font-weight: 600; font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
