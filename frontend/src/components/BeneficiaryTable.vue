<template>
  <div class="space-y-4">
    <!-- Beneficiaries -->
    <div>
      <p class="label mb-2">Beneficiaries <span class="required-asterisk">*</span></p>

      <div v-if="!rows.length" class="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-400">
        No beneficiaries added yet — select one from your HR records or add manually below.
      </div>

      <div v-else class="space-y-3">
        <div v-for="(row, idx) in rows" :key="idx" class="rounded-lg border border-gray-200 p-3">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-xs font-semibold text-gray-500">#{{ idx + 1 }}</span>
              <span
                v-if="row.source === 'Business Central'"
                class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-100 text-indigo-700"
              >Imported from HR records</span>
              <span
                v-else
                class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-500"
              >Added by you</span>
              <span
                v-if="isMinor(row)"
                class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-700"
              >Under 18 — guardian & birth certificate required</span>
            </div>
            <button v-if="editable" type="button" class="text-xs text-error hover:underline" @click="removeRow(idx)">
              Remove
            </button>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div>
              <label class="label">Name <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="row.full_name" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Email</label>
              <input type="email" class="input-field" v-model="row.email" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Mobile</label>
              <input type="text" class="input-field" v-model="row.mobile" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Date of Birth</label>
              <input type="date" class="input-field" v-model="row.date_of_birth" :disabled="!editable" />
            </div>
            <div v-if="!isMinor(row)">
              <label class="label">ID No.</label>
              <input type="text" class="input-field" v-model="row.id_number" :disabled="!editable" />
            </div>
            <div v-if="isMinor(row)">
              <label class="label">Birth Certificate No. <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="row.birth_certificate_no" :disabled="!editable" />
            </div>
            <div v-if="isMinor(row)">
              <label class="label">Guardian <span class="required-asterisk">*</span></label>
              <button
                type="button"
                class="input-field text-left flex items-center justify-between gap-2"
                :class="guardianFor(row) ? 'text-gray-800' : 'text-gray-400'"
                :disabled="!editable"
                @click="openGuardianModal(row)"
              >
                <span class="truncate">
                  {{ guardianFor(row) ? guardianFor(row).guardian_name + ' (' + guardianFor(row).relationship_to_beneficiary + ')' : 'Select or add guardian…' }}
                </span>
                <svg class="w-4 h-4 flex-shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
              </button>
            </div>
            <div>
              <label class="label">Relationship to Member <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="row.relationship" :disabled="!editable" list="relationship-options" />
            </div>
            <div>
              <label class="label">% Share <span class="required-asterisk">*</span></label>
              <input type="number" min="0" max="100" step="0.01" class="input-field" v-model.number="row.share_percent" :disabled="!editable" />
            </div>
          </div>
        </div>
      </div>

      <!-- Add controls: select from HR records, add manually, or add a guardian -->
      <div v-if="editable" class="mt-3 flex flex-wrap items-center gap-2">
        <select
          v-if="suggestions.length"
          class="input-field !w-auto min-w-[16rem] text-sm"
          v-model="selectedSuggestion"
          @change="onSelectSuggestion"
        >
          <option value="" disabled>Select beneficiary from HR records…</option>
          <option v-for="(s, i) in suggestions" :key="i" :value="String(i)">
            {{ s.full_name || '(unnamed)' }}{{ s.relationship ? ' — ' + s.relationship : '' }}{{ s.bc_category ? ' (' + s.bc_category + ')' : '' }}
          </option>
        </select>
        <span v-if="suggestions.length" class="text-xs text-gray-400">or</span>
        <button type="button" class="btn-secondary !py-1.5 text-xs" @click="addRow">
          + Add beneficiary manually
        </button>
      </div>

      <datalist id="relationship-options">
        <option value="Spouse" /><option value="Son" /><option value="Daughter" />
        <option value="Father" /><option value="Mother" /><option value="Brother" />
        <option value="Sister" /><option value="Other" />
      </datalist>

      <!-- Allocation total -->
      <div v-if="rows.length" class="mt-3">
        <div class="flex items-center justify-between text-xs mb-1">
          <span class="font-medium" :class="totalOk ? 'text-green-700' : 'text-error'">
            Total allocation: {{ totalShare.toFixed(2) }}% {{ totalOk ? '✓' : '(must equal 100%)' }}
          </span>
        </div>
        <div class="h-2 rounded-full bg-gray-100 overflow-hidden">
          <div
            class="h-full transition-all"
            :class="totalOk ? 'bg-green-500' : totalShare > 100 ? 'bg-red-500' : 'bg-amber-400'"
            :style="{ width: Math.min(totalShare, 100) + '%' }"
          />
        </div>
      </div>
    </div>

    <!-- Guardians list (at the bottom) -->
    <div v-if="minors.length || guardians.length">
      <p class="label mb-2">Guardians (for beneficiaries under 18)</p>

      <div v-if="!guardians.length" class="rounded-lg border border-dashed border-amber-300 bg-amber-50 p-3 text-xs text-amber-700">
        {{ minors.length }} beneficiar{{ minors.length === 1 ? 'y is' : 'ies are' }} under 18 — use the Guardian field on each under-18 beneficiary to add one.
      </div>

      <div v-else class="divide-y divide-gray-100 rounded-lg border border-gray-200">
        <div v-for="(g, idx) in guardians" :key="idx" class="flex items-center justify-between gap-3 px-3 py-2.5 text-sm">
          <div class="min-w-0 flex-1">
            <p class="font-medium text-gray-800 truncate">{{ g.guardian_name }}</p>
            <p class="text-xs text-gray-500 truncate">
              Guardian of <span class="font-medium">{{ g.beneficiary_name }}</span>
              · {{ g.relationship_to_beneficiary }}
              <template v-if="g.id_number"> · ID {{ g.id_number }}</template>
              <template v-if="g.mobile"> · {{ g.mobile }}</template>
              <template v-if="g.email"> · {{ g.email }}</template>
            </p>
          </div>
          <div v-if="editable" class="flex items-center gap-3 flex-shrink-0">
            <button type="button" class="text-xs text-primary hover:underline" @click="editGuardian(idx)">Edit</button>
            <button type="button" class="text-xs text-error hover:underline" @click="removeGuardian(idx)">Remove</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Guardian modal: select an existing person or add a new one -->
    <div v-if="showGuardianModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40" @click="closeGuardianModal" />
      <div class="relative w-full max-w-lg card p-5 max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-navy">{{ editingIndex === null ? 'Add Guardian' : 'Edit Guardian' }}</h3>
          <button type="button" class="text-gray-400 hover:text-navy" @click="closeGuardianModal">✕</button>
        </div>

        <!-- Select an existing person to prefill -->
        <div v-if="guardianCandidates.length" class="mb-4">
          <label class="label">Select an existing person</label>
          <select class="input-field" v-model="selectedCandidate" @change="onSelectCandidate">
            <option value="">— fill in manually below —</option>
            <option v-for="(c, i) in guardianCandidates" :key="i" :value="String(i)">
              {{ c.full_name }}{{ c.hint ? ' — ' + c.hint : '' }}
            </option>
          </select>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="sm:col-span-2">
            <label class="label">Guardian Name <span class="required-asterisk">*</span></label>
            <input type="text" class="input-field" v-model="guardianDraft.guardian_name" />
          </div>
          <div>
            <label class="label">Email</label>
            <input type="email" class="input-field" v-model="guardianDraft.email" />
          </div>
          <div>
            <label class="label">Mobile</label>
            <input type="text" class="input-field" v-model="guardianDraft.mobile" />
          </div>
          <div>
            <label class="label">ID No.</label>
            <input type="text" class="input-field" v-model="guardianDraft.id_number" />
          </div>
          <div>
            <label class="label">Guardian of (Beneficiary)</label>
            <input type="text" class="input-field bg-gray-50" :value="guardianDraft.beneficiary_name" disabled />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Relationship to Beneficiary <span class="required-asterisk">*</span></label>
            <input type="text" class="input-field" v-model="guardianDraft.relationship_to_beneficiary" placeholder="e.g. Mother, Uncle" />
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-5">
          <button type="button" class="btn-secondary" @click="closeGuardianModal">Cancel</button>
          <button type="button" class="btn-primary" :disabled="!guardianDraftValid" @click="saveGuardian">
            {{ editingIndex === null ? 'Add Guardian' : 'Save Changes' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  rows: { type: Array, required: true },
  guardians: { type: Array, required: true },
  editable: { type: Boolean, default: true },
  suggestions: { type: Array, default: () => [] },
})

const emit = defineEmits(['add-suggestion'])

const selectedSuggestion = ref('')

function onSelectSuggestion() {
  const idx = Number(selectedSuggestion.value)
  const s = props.suggestions[idx]
  if (s) emit('add-suggestion', s)
  selectedSuggestion.value = ''
}

// When a date of birth crosses the 18-year line, swap the identifier: adults
// carry an ID number, minors a birth certificate number. The irrelevant
// field hides itself and its stale value is dropped.
watch(
  () => props.rows.map((r) => r.date_of_birth),
  () => {
    for (const row of props.rows) {
      if (row.birth_certificate_no && !isMinor(row)) {
        row.birth_certificate_no = ''
      }
      if (row.id_number && isMinor(row)) {
        row.id_number = ''
      }
    }
  }
)

function isMinor(row) {
  if (!row.date_of_birth) return false
  const dob = new Date(row.date_of_birth)
  if (isNaN(dob)) return false
  const now = new Date()
  let age = now.getFullYear() - dob.getFullYear()
  if (now.getMonth() < dob.getMonth() || (now.getMonth() === dob.getMonth() && now.getDate() < dob.getDate())) age--
  return age < 18
}

const minors = computed(() => props.rows.filter(isMinor))
const beneficiaryNames = computed(() => props.rows.map((r) => (r.full_name || '').trim()).filter(Boolean))
const totalShare = computed(() => props.rows.reduce((sum, r) => sum + (Number(r.share_percent) || 0), 0))
const totalOk = computed(() => Math.abs(totalShare.value - 100) <= 0.01)

function addRow() {
  props.rows.push({
    full_name: '', email: '', mobile: '', date_of_birth: '', id_number: '',
    birth_certificate_no: '', relationship: '', share_percent: null,
    source: 'Manual', bc_relative_no: '', bc_line_no: 0, bc_category: '',
  })
}
function removeRow(idx) {
  const row = props.rows[idx]
  props.rows.splice(idx, 1)
  // Drop any guardian that belonged to the removed beneficiary.
  if (row?._key) {
    const gIdx = props.guardians.findIndex((g) => g._ben_key === row._key)
    if (gIdx >= 0) props.guardians.splice(gIdx, 1)
  }
}
function removeGuardian(idx) {
  props.guardians.splice(idx, 1)
}

// ---- Guardian modal ----
const showGuardianModal = ref(false)
const editingIndex = ref(null)
const selectedCandidate = ref('')
const emptyGuardian = () => ({
  guardian_name: '', email: '', mobile: '', id_number: '',
  beneficiary_name: '', relationship_to_beneficiary: '',
})
const guardianDraft = ref(emptyGuardian())

const minorNames = computed(() =>
  minors.value.map((r) => (r.full_name || '').trim()).filter(Boolean)
)

// People who can be picked as a guardian: guardians already entered for
// other beneficiaries first (so the same person is one click for the next
// child), then adult beneficiaries on the form, then HR-record relatives.
const guardianCandidates = computed(() => {
  const seen = new Set()
  const list = []
  for (const g of props.guardians) {
    const name = (g.guardian_name || '').trim()
    if (!name || seen.has(name)) continue
    // Don't offer the guardian being edited as a candidate for itself.
    if (editingIndex.value !== null && props.guardians[editingIndex.value] === g) continue
    seen.add(name)
    list.push({
      full_name: name, email: g.email || '', mobile: g.mobile || '', id_number: g.id_number || '',
      relationship: g.relationship_to_beneficiary || '',
      hint: `guardian of ${g.beneficiary_name}`,
      isGuardian: true,
    })
  }
  for (const r of props.rows) {
    const name = (r.full_name || '').trim()
    if (!name || isMinor(r) || seen.has(name)) continue
    seen.add(name)
    list.push({ full_name: name, email: r.email || '', mobile: r.mobile || '', id_number: r.id_number || '', hint: r.relationship ? `${r.relationship} (beneficiary)` : 'beneficiary' })
  }
  for (const s of props.suggestions) {
    const name = (s.full_name || '').trim()
    if (!name || seen.has(name)) continue
    seen.add(name)
    list.push({ full_name: name, email: '', mobile: s.mobile || '', id_number: s.id_number || '', hint: s.relationship ? `${s.relationship} (HR records)` : 'HR records' })
  }
  return list
})

const guardianDraftValid = computed(() =>
  (guardianDraft.value.guardian_name || '').trim()
  && (guardianDraft.value.beneficiary_name || '').trim()
  && (guardianDraft.value.relationship_to_beneficiary || '').trim()
)

// ---- Row/guardian linkage ----
// Guardians are linked to a specific beneficiary ROW via a client-side key,
// not by name — several beneficiaries can share a name (e.g. imported HR
// rows), and a name match would wrongly attach one guardian to all of them.
// The keys are stripped server-side; on reload they are re-linked by claiming
// name matches one-to-one.
let keyCounter = 0

function ensureKeys() {
  for (const r of props.rows) {
    if (!r._key) r._key = `b${++keyCounter}`
  }
  const claimed = new Set(props.guardians.map((g) => g._ben_key).filter(Boolean))
  for (const g of props.guardians) {
    if (g._ben_key) continue
    const row = props.rows.find(
      (r) =>
        !claimed.has(r._key) &&
        (r.full_name || '').trim() === (g.beneficiary_name || '').trim()
    )
    if (row) {
      g._ben_key = row._key
      claimed.add(row._key)
    }
  }
  // Follow renames: keep the stored beneficiary_name matching the linked row.
  for (const g of props.guardians) {
    const row = props.rows.find((r) => r._key === g._ben_key)
    if (row && (row.full_name || '').trim()) g.beneficiary_name = row.full_name.trim()
  }
}

watch(
  () => `${props.rows.length}:${props.guardians.length}:${props.rows.map((r) => r.full_name).join('|')}`,
  ensureKeys,
  { immediate: true }
)

function guardianFor(row) {
  if (!row._key) return null
  return props.guardians.find((g) => g._ben_key === row._key) || null
}

function openGuardianModal(row) {
  ensureKeys()
  const existingIdx = props.guardians.findIndex((g) => g._ben_key === row._key)
  editingIndex.value = existingIdx >= 0 ? existingIdx : null
  selectedCandidate.value = ''
  guardianDraft.value = existingIdx >= 0
    ? { ...props.guardians[existingIdx] }
    : { ...emptyGuardian(), beneficiary_name: (row.full_name || '').trim(), _ben_key: row._key }
  showGuardianModal.value = true
}

function editGuardian(idx) {
  editingIndex.value = idx
  selectedCandidate.value = ''
  guardianDraft.value = { ...props.guardians[idx] }
  showGuardianModal.value = true
}

function onSelectCandidate() {
  const c = guardianCandidates.value[Number(selectedCandidate.value)]
  if (!c) return

  // Picking an existing guardian assigns them to this beneficiary
  // immediately — no form-filling, the modal just closes.
  if (c.isGuardian) {
    const assigned = {
      ...guardianDraft.value,
      guardian_name: c.full_name,
      email: c.email,
      mobile: c.mobile,
      id_number: c.id_number,
      relationship_to_beneficiary: c.relationship || guardianDraft.value.relationship_to_beneficiary,
    }
    if (editingIndex.value === null) {
      props.guardians.push(assigned)
    } else {
      Object.assign(props.guardians[editingIndex.value], assigned)
    }
    closeGuardianModal()
    return
  }

  guardianDraft.value.guardian_name = c.full_name
  guardianDraft.value.email = c.email
  guardianDraft.value.mobile = c.mobile
  guardianDraft.value.id_number = c.id_number
}

function saveGuardian() {
  if (!guardianDraftValid.value) return
  if (editingIndex.value === null) {
    props.guardians.push({ ...guardianDraft.value })
  } else {
    Object.assign(props.guardians[editingIndex.value], guardianDraft.value)
  }
  closeGuardianModal()
}

function closeGuardianModal() {
  showGuardianModal.value = false
  editingIndex.value = null
}

defineExpose({ totalOk, minors, isMinor })
</script>
