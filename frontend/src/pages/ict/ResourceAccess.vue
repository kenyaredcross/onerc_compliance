<template>
  <div class="ict-shell">
    <router-link to="/ict-help" class="ict-back">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
      Back
    </router-link>

    <header style="margin-top: 20px; max-width: 640px;">
      <p class="ict-eyebrow">Service Catalogue</p>
      <h1 class="ict-display" style="font-size: clamp(30px, 5vw, 44px); margin: 12px 0 0;">Request a resource</h1>
      <p class="ict-muted" style="margin-top: 12px; font-size: 16px;">
        Choose what you need — requests route to ICT for approval where required.
      </p>
    </header>

    <div style="margin-top: 26px; max-width: 520px;">
      <input v-model="q" class="ict-search" placeholder="Search the catalogue…" />
    </div>

    <div v-if="loading" style="margin-top: 36px; display: grid; gap: 14px;">
      <div v-for="n in 6" :key="n" class="ict-skel" style="height: 76px;"></div>
    </div>

    <div v-else-if="!filteredGroups.length" class="ict-card" style="margin-top: 36px; padding: 48px; text-align: center;">
      <p class="ict-muted">No catalogue items match "{{ q }}".</p>
    </div>

    <div v-else style="margin-top: 36px; display: flex; flex-direction: column; gap: 38px;">
      <section v-for="(group, gi) in filteredGroups" :key="group.category" class="ict-rise" :style="{ animationDelay: gi * 60 + 'ms' }">
        <h2 class="ict-display" style="font-size: 20px; margin: 0 0 14px;">{{ group.category }}</h2>
        <div class="ict-cat-grid">
          <button v-for="item in group.items" :key="item.name" class="ict-card ict-item" @click="open(item, group.category)">
            <span class="ict-item-icon">{{ initialOf(item.item_name) }}</span>
            <span style="flex: 1; min-width: 0;">
              <span style="display: flex; align-items: center; gap: 8px;">
                <span class="ict-item-name">{{ item.item_name }}</span>
                <span v-if="item.requires_ict_approval" class="ict-badge ict-badge-pending">Approval</span>
              </span>
              <span class="ict-muted ict-item-desc">{{ item.description || item.service || 'Tap to request' }}</span>
            </span>
            <svg class="ict-item-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6" /></svg>
          </button>
        </div>
      </section>
    </div>

    <transition name="ict-fade">
      <div v-if="active" class="ict-modal-backdrop" @click.self="close">
        <div class="ict-modal">
          <p class="ict-eyebrow">{{ activeCategory }}</p>
          <h3 class="ict-display" style="font-size: 24px; margin: 8px 0 0;">{{ active.item_name }}</h3>
          <p v-if="active.description" class="ict-muted" style="margin-top: 8px; font-size: 14px;">{{ active.description }}</p>

          <div style="margin-top: 18px;">
            <label class="ict-label">Anything we should know?</label>
            <textarea v-model="note" class="ict-textarea" placeholder="Optional details — model, location, why you need it…"></textarea>
          </div>

          <p v-if="active.requires_ict_approval" class="ict-muted" style="font-size: 13px; margin-top: 12px; display: flex; gap: 7px; align-items: flex-start;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0; margin-top: 1px;"><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></svg>
            This request needs ICT approval (AUP 10.3) before it's fulfilled.
          </p>

          <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 22px;">
            <button class="ict-btn ict-btn-ghost" @click="close" :disabled="submitting">Cancel</button>
            <button class="ict-btn ict-btn-accent" @click="submit" :disabled="submitting">
              {{ submitting ? 'Submitting…' : 'Submit request' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi.js'
import { useToast } from '@/composables/useToast.js'

const PFX = 'onerc_compliance.onerc_incident_management.portal.'
const api = useApi()
const toast = useToast()
const router = useRouter()

const groups = ref([])
const loading = ref(true)
const q = ref('')
const active = ref(null)
const activeCategory = ref('')
const note = ref('')
const submitting = ref(false)

onMounted(async () => {
  try {
    groups.value = await api.call(PFX + 'get_catalogue')
  } catch (e) {
    toast.error(e.message || 'Could not load the catalogue.')
  } finally {
    loading.value = false
  }
})

const filteredGroups = computed(() => {
  const term = q.value.trim().toLowerCase()
  if (!term) return groups.value
  return groups.value
    .map((g) => ({
      ...g,
      items: g.items.filter((i) =>
        `${i.item_name} ${i.description || ''} ${i.service || ''}`.toLowerCase().includes(term)
      ),
    }))
    .filter((g) => g.items.length)
})

function initialOf(name) {
  return (name?.[0] || '?').toUpperCase()
}
function open(item, category) {
  active.value = item
  activeCategory.value = category || item.service_category || 'Catalogue'
  note.value = ''
}
function close() {
  if (!submitting.value) active.value = null
}
async function submit() {
  submitting.value = true
  try {
    const res = await api.call(PFX + 'submit_service_request', {
      catalogue_item: active.value.name,
      subject: active.value.item_name,
      description: note.value,
    })
    toast.success(`Request ${res.name} submitted.`)
    active.value = null
    router.push('/ict-help/support')
  } catch (e) {
    toast.error(e.message || 'Could not submit your request.')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.ict-cat-grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
@media (min-width: 640px) { .ict-cat-grid { grid-template-columns: 1fr 1fr; } }
.ict-item { display: flex; align-items: center; gap: 14px; padding: 15px 18px; text-align: left; cursor: pointer; font: inherit; width: 100%; }
.ict-item-icon { width: 42px; height: 42px; border-radius: 11px; background: var(--accent-soft); color: var(--accent-ink); display: grid; place-items: center; font-weight: 700; font-size: 16px; flex-shrink: 0; font-family: var(--font-display); }
.ict-item-name { font-weight: 600; font-size: 15.5px; }
.ict-item-desc { display: block; font-size: 13.5px; margin: 3px 0 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ict-item-arrow { width: 18px; height: 18px; color: #c9c1b5; flex-shrink: 0; transition: transform 0.2s, color 0.2s; }
.ict-item:hover .ict-item-arrow { color: var(--accent); transform: translateX(3px); }

.ict-modal-backdrop { position: fixed; inset: 0; background: rgba(27, 26, 24, 0.42); backdrop-filter: blur(3px); display: grid; place-items: center; padding: 20px; z-index: 50; }
.ict-modal { background: var(--paper-2); border: 1px solid var(--line); border-radius: 20px; box-shadow: 0 30px 80px -20px rgba(20, 18, 15, 0.45); padding: 28px; width: 100%; max-width: 460px; }
</style>
