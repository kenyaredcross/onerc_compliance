<template>
  <div class="p-6 max-w-4xl mx-auto">
    <div class="mb-6">
      <h2 class="text-xl font-bold text-navy">Pension Compliance</h2>
      <p class="text-sm text-gray-500 mt-0.5">
        Confirm your occupational scheme details and nominate your beneficiaries.
      </p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-16 text-gray-400">
      <svg class="animate-spin w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      Loading your forms…
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="card p-4 border-l-4 border-error text-error text-sm">
      {{ loadError }}
    </div>

    <template v-else>
      <!-- Notices -->
      <div
        v-if="settings.staff_instructions"
        class="card p-4 mb-4 text-sm text-gray-700 prose prose-sm max-w-none"
        v-html="settings.staff_instructions"
      />
      <div v-if="!settings.enrolment_open" class="card p-4 mb-4 border-l-4 border-amber-400 text-sm text-amber-800 bg-amber-50">
        Enrolment is currently closed. You can view your forms but cannot submit changes.
      </div>
      <div v-if="bc.status === 'unavailable'" class="card p-4 mb-4 border-l-4 border-amber-400 text-sm text-amber-800 bg-amber-50">
        {{ bc.error || 'HR records are unreachable right now; you can still fill the forms manually.' }}
      </div>

      <!-- Form state banners -->
      <FormStateBanner :form="forms.scheme"     label="Occupational Scheme Form"  @start-new="startNew('scheme')"     class="mb-3" />
      <FormStateBanner :form="forms.nomination" label="Beneficiary Nomination"     @start-new="startNew('nomination')" class="mb-4" />

      <div class="space-y-6">

        <!-- ═══ PART 1: EMPLOYMENT DETAILS ═══ -->
        <div class="card p-5 space-y-5">
          <h3 class="section-title !border-b-2 !border-navy/20 text-base">Part 1 — Employment Details</h3>

          <div class="rounded-lg bg-green-50 border border-green-200 p-3 text-xs text-green-800">
            Details below are prefilled from your HR record — please confirm they are correct and complete the rest.
          </div>

          <MemberBasicInfo :model-value="scheme" :scheme-name="settings.scheme_name" :editable="schemeEditable">
            <div>
              <label class="label">Occupation</label>
              <input type="text" class="input-field" v-model="scheme.occupation" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Date of Birth <span class="required-asterisk">*</span></label>
              <input type="date" class="input-field" v-model="scheme.date_of_birth" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Member Number <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="scheme.member_number" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Date of Admission to the Scheme</label>
              <input type="date" class="input-field" v-model="scheme.date_of_admission" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Date of Appointment</label>
              <input type="date" class="input-field" v-model="scheme.date_of_appointment" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Marital Status</label>
              <select class="input-field" v-model="nomination.marital_status" :disabled="!nominationEditable">
                <option value="">Select…</option>
                <option>Single</option><option>Married</option><option>Divorced</option><option>Widowed</option>
              </select>
            </div>
          </MemberBasicInfo>

          <label class="flex items-start gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" class="mt-0.5" v-model="scheme.details_confirmed" :disabled="!schemeEditable" />
            I confirm the employment details above are correct.
          </label>
        </div>

        <!-- ═══ PART 2: BANK DETAILS ═══ -->
        <div class="card p-5 space-y-4">
          <h3 class="section-title !border-b-2 !border-navy/20 text-base">Part 2 — Bank Details</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="label">Account Name <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="scheme.bank_account_name" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Bank <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="scheme.bank_name" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Bank Branch</label>
              <input type="text" class="input-field" v-model="scheme.bank_branch" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Account Number <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="scheme.bank_account_number" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Town/City</label>
              <input type="text" class="input-field" v-model="scheme.bank_town_city" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Bank Code</label>
              <input type="text" class="input-field" v-model="scheme.bank_code" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Branch Code</label>
              <input type="text" class="input-field" v-model="scheme.branch_code" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">SWIFT Code</label>
              <input type="text" class="input-field" v-model="scheme.swift_code" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">SORT Code/IBAN Code</label>
              <input type="text" class="input-field" v-model="scheme.sort_or_iban_code" :disabled="!schemeEditable" />
            </div>
          </div>
        </div>

        <!-- ═══ PART 3: ADDITIONAL VOLUNTARY CONTRIBUTIONS ═══ -->
        <div class="card p-5 space-y-3">
          <h3 class="section-title !border-b-2 !border-navy/20 text-base">
            Part 3 — Additional Voluntary Contributions
            <span class="text-gray-400 font-normal text-xs ml-1">(optional)</span>
          </h3>
          <p class="text-xs text-gray-500">
            Deduction from your salary paid to {{ settings.administrator_name || 'the scheme administrator' }} over and above
            your normal monthly contributions. Fill either an amount <em>or</em> a percentage, not both.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="label">Amount (Kshs per month)</label>
              <input type="number" min="0" step="0.01" class="input-field" v-model.number="scheme.avc_amount" :disabled="!schemeEditable" />
            </div>
            <div>
              <label class="label">Percent (% per month)</label>
              <input type="number" min="0" max="100" step="0.01" class="input-field" v-model.number="scheme.avc_percent" :disabled="!schemeEditable" />
            </div>
          </div>
          <p v-if="scheme.avc_amount && scheme.avc_percent" class="text-xs text-error">
            Fill either an amount or a percentage — not both.
          </p>
        </div>

        <!-- ═══ PART 4: BENEFICIARY NOMINATION ═══ -->
        <div class="card p-5 space-y-4">
          <h3 class="section-title !border-b-2 !border-navy/20 text-base">Part 4 — Beneficiary Nomination</h3>
          <p v-if="settings.nomination_statement" class="text-xs text-gray-600 italic" v-html="settings.nomination_statement" />
          <BeneficiaryTable
            ref="nominationTable"
            :rows="nomination.beneficiaries"
            :guardians="nomination.guardians"
            :editable="nominationEditable"
            :suggestions="availableSuggestions()"
            @add-suggestion="addSuggestion($event)"
          />
          <p class="text-xs text-gray-500">
            NB: If beneficiaries are under 18 years of age, kindly indicate the Birth Certificate No.
          </p>
        </div>

        <!-- ═══ PART 5: DECLARATION ═══ -->
        <div class="card p-5 space-y-4">
          <h3 class="section-title !border-b-2 !border-navy/20 text-base">Part 5 — Declaration</h3>
          <p v-if="settings.declaration_text" class="text-xs text-gray-600 italic" v-html="settings.declaration_text" />

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="label">Signed At (Place)</label>
              <input type="text" class="input-field" v-model="nomination.signed_at" :disabled="!nominationEditable" placeholder="e.g. Nairobi" />
            </div>
          </div>

          <label class="flex items-start gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" class="mt-0.5" v-model="bothDeclared" :disabled="!anyEditable" @change="onBothDeclared" />
            I hereby declare that all statements and answers above are complete and true, that I agree to the Scheme Rules,
            and understand this nomination nullifies any previous nomination I submitted to the scheme trustees.
            <span class="required-asterisk">*</span>
          </label>
          <p class="text-xs text-gray-400">
            It is your responsibility to update the Trustees on any changes in the details given above.
          </p>
        </div>

        <!-- ═══ ACTIONS ═══ -->
        <div v-if="anyEditable" class="card p-4 flex items-center gap-3">
          <button type="button" class="btn-secondary" :disabled="saving" @click="saveBoth(false)">
            Save Draft
          </button>
          <button
            type="button"
            class="btn-primary"
            :disabled="saving || !bothDeclared || !settings.enrolment_open"
            @click="saveBoth(true)"
          >
            Submit
          </button>
          <span v-if="saving" class="text-xs text-gray-400">Saving…</span>
        </div>

      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, h } from 'vue'
import { useApi } from '../composables/useApi.js'
import { useToast } from '../composables/useToast.js'
import StatusBadge from '../components/StatusBadge.vue'
import BeneficiaryTable from '../components/BeneficiaryTable.vue'
import MemberBasicInfo from '../components/MemberBasicInfo.vue'

const api = useApi()
const toast = useToast()

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)

const settings = ref({})
const employeePrefill = ref({})
const forms = ref({ scheme: {}, nomination: {} })
const bc = ref({ status: 'skipped', error: '', suggestions: [] })
const startedNew = reactive({ scheme: false, nomination: false })

// Single declaration checkbox that drives both forms
const bothDeclared = ref(false)
function onBothDeclared() {
  scheme.declaration_accepted = bothDeclared.value
  nomination.declaration_accepted = bothDeclared.value
}

const emptyScheme = () => ({
  member_full_name: '', occupation: '', date_of_birth: '', member_number: '',
  date_of_admission: '', date_of_appointment: '', mobile_number: '', email: '',
  kra_pin: '', id_number: '', details_confirmed: false,
  avc_amount: null, avc_percent: null,
  bank_account_name: '', bank_name: '', bank_branch: '', bank_account_number: '',
  bank_town_city: '', bank_code: '', branch_code: '', swift_code: '', sort_or_iban_code: '',
  declaration_accepted: false,
  beneficiaries: [], guardians: [],
})

const emptyNomination = () => ({
  member_full_name: '', email: '', telephone: '', marital_status: '',
  id_number: '', kra_pin: '',
  declaration_accepted: false, signed_at: '',
  beneficiaries: [], guardians: [],
})

const scheme = reactive(emptyScheme())
const nomination = reactive(emptyNomination())

const schemeEditable = computed(() => {
  const f = forms.value.scheme
  if (startedNew.scheme) return true
  if (!f?.doc) return true
  return ['Draft', 'Needs More Info'].includes(f.doc.status)
})
const nominationEditable = computed(() => {
  const f = forms.value.nomination
  if (startedNew.nomination) return true
  if (!f?.doc) return true
  return ['Draft', 'Needs More Info'].includes(f.doc.status)
})
const anyEditable = computed(() => schemeEditable.value || nominationEditable.value)

// Inline banner component
const FormStateBanner = {
  props: ['form', 'label'],
  emits: ['start-new'],
  setup(props, { emit }) {
    return () => {
      const doc = props.form?.doc
      if (!doc) return null
      const status = doc.status
      const messages = {
        Submitted: `${props.label} has been submitted and is awaiting review.`,
        Reviewed: `${props.label} has been reviewed and accepted.`,
        Rejected: `${props.label} was rejected.`,
        Superseded: `${props.label} has been superseded by a newer submission.`,
        'Needs More Info': null,
      }
      const children = []
      if (status === 'Needs More Info') {
        const remark = (doc.review_actions || []).slice().reverse().find((a) => a.action === 'Needs More Info')
        children.push(
          h('div', { class: 'rounded-lg bg-orange-50 border border-orange-200 p-3 text-sm' }, [
            h('p', { class: 'font-semibold text-orange-800 mb-1' }, `${props.label} — more information needed`),
            h('p', { class: 'text-orange-700' }, remark?.remarks || 'No remark provided.'),
          ])
        )
      } else if (messages[status]) {
        children.push(
          h('div', { class: 'rounded-lg bg-blue-50 border border-blue-200 p-3 text-sm text-blue-800 flex items-center justify-between gap-3' }, [
            h('span', {}, `${messages[status]} (${doc.name})`),
            props.form.can_start_new
              ? h('button', {
                  type: 'button',
                  class: 'text-xs font-semibold text-primary hover:underline whitespace-nowrap',
                  onClick: () => emit('start-new'),
                }, 'Fill a new form')
              : null,
          ])
        )
      }
      return children.length ? h('div', {}, children) : null
    }
  },
}

function availableSuggestions() {
  const used = new Set(nomination.beneficiaries.map((b) => b.bc_relative_no).filter(Boolean))
  return (bc.value.suggestions || []).filter((s) => !s.bc_relative_no || !used.has(s.bc_relative_no))
}

function addSuggestion(s) {
  nomination.beneficiaries.push({
    full_name: s.full_name || '',
    email: '',
    mobile: s.mobile || '',
    date_of_birth: s.date_of_birth || '',
    id_number: s.id_number || '',
    birth_certificate_no: '',
    relationship: s.relationship || '',
    share_percent: null,
    source: 'Business Central',
    bc_relative_no: s.bc_relative_no || '',
    bc_line_no: s.bc_line_no || 0,
    bc_category: s.bc_category || '',
  })
}

function applyPrefill() {
  const p = employeePrefill.value
  scheme.member_full_name = p.employee_name || ''
  scheme.occupation = p.designation || ''
  scheme.date_of_birth = p.date_of_birth || ''
  scheme.date_of_appointment = p.date_of_joining || ''
  scheme.mobile_number = p.cell_number || ''
  scheme.email = p.email || ''
  nomination.member_full_name = p.employee_name || ''
  nomination.email = p.email || ''
  nomination.telephone = p.cell_number || ''
}

function prepopulateBeneficiaries() {
  if (nomination.beneficiaries.length) return
  ;(bc.value.suggestions || []).forEach((s) => addSuggestion(s))
}

function hydrateScheme() {
  const doc = forms.value.scheme?.doc
  if (!doc) { applyPrefill(); return }
  Object.keys(scheme).forEach((field) => {
    if (field === 'beneficiaries' || field === 'guardians') return
    if (doc[field] !== undefined && doc[field] !== null) scheme[field] = doc[field]
  })
  scheme.declaration_accepted = Boolean(doc.declaration_accepted)
  scheme.details_confirmed = Boolean(doc.details_confirmed)
}

function hydrateNomination() {
  const doc = forms.value.nomination?.doc
  if (!doc) { prepopulateBeneficiaries(); return }
  Object.keys(nomination).forEach((field) => {
    if (field === 'beneficiaries' || field === 'guardians') return
    if (doc[field] !== undefined && doc[field] !== null) nomination[field] = doc[field]
  })
  nomination.declaration_accepted = Boolean(doc.declaration_accepted)
  nomination.beneficiaries = (doc.beneficiaries || []).map((b) => ({ ...b }))
  nomination.guardians = (doc.guardians || []).map((g) => ({ ...g }))
  prepopulateBeneficiaries()
}

function syncSharedFields() {
  // Keep nomination in sync with scheme for the shared basic fields
  nomination.member_full_name = scheme.member_full_name
  nomination.email = scheme.email
  nomination.telephone = scheme.mobile_number
  nomination.id_number = scheme.id_number
  nomination.kra_pin = scheme.kra_pin
}

function startNew(key) {
  startedNew[key] = true
  if (key === 'scheme') {
    Object.assign(scheme, emptyScheme())
    applyPrefill()
  } else {
    Object.assign(nomination, emptyNomination())
    applyPrefill()
    prepopulateBeneficiaries()
  }
  bothDeclared.value = false
  toast.info('Started a new form — it will amend your previous one when submitted.')
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.call('onerc_compliance.api.v1.scheme.get_my_forms')
    if (res.status !== 'success') {
      loadError.value = res.message || 'Failed to load your forms.'
      return
    }
    settings.value = res.data.settings || {}
    employeePrefill.value = res.data.employee_prefill || {}
    forms.value = res.data.forms || { scheme: {}, nomination: {} }
    bc.value = res.data.bc || { status: 'skipped', error: '', suggestions: [] }
    hydrateScheme()
    hydrateNomination()
    bothDeclared.value = Boolean(scheme.declaration_accepted && nomination.declaration_accepted)
  } catch (e) {
    loadError.value = e.message || 'Failed to load your forms.'
  } finally {
    loading.value = false
  }
}

async function saveOne(key, submit) {
  const state = key === 'scheme' ? scheme : nomination
  const payload = { ...state, declaration_accepted: state.declaration_accepted ? 1 : 0 }
  if (key === 'scheme') payload.details_confirmed = state.details_confirmed ? 1 : 0
  const res = await api.call('onerc_compliance.api.v1.scheme.save_form', {
    form_type: key,
    payload,
    submit: submit ? 1 : 0,
  })
  if (res.status !== 'success') throw new Error(res.message || 'Save failed.')
  startedNew[key] = false
  return res
}

async function saveBoth(submit) {
  if (submit) {
    if (scheme.avc_amount && scheme.avc_percent) {
      toast.error('Additional Voluntary Contributions: fill either an amount or a percentage, not both.')
      return
    }
    if (!nomination.beneficiaries.length) {
      toast.error('Add at least one beneficiary before submitting.')
      return
    }
    if (nominationTable.value && !nominationTable.value.totalOk) {
      toast.error('Beneficiary % shares must total exactly 100.')
      return
    }
  }

  // Sync shared fields from scheme → nomination before saving
  syncSharedFields()

  saving.value = true
  try {
    const tasks = []
    if (schemeEditable.value) tasks.push(saveOne('scheme', submit))
    if (nominationEditable.value) tasks.push(saveOne('nomination', submit))
    await Promise.all(tasks)
    toast.success(submit ? 'Forms submitted for review.' : 'Draft saved.')
    await load()
  } catch (e) {
    toast.error(e.message || 'Save failed.')
  } finally {
    saving.value = false
  }
}

const nominationTable = ref(null)

onMounted(load)
</script>

<style scoped>
.section-title {
  @apply text-sm font-bold text-navy mb-3 pb-1 border-b border-gray-100;
}
</style>
