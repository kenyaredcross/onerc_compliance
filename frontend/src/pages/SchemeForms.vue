<template>
  <div class="p-6 max-w-4xl mx-auto">
    <div class="mb-6 flex items-start justify-between flex-wrap gap-2">
      <div>
        <h2 class="text-xl font-bold text-navy">Pension Compliance</h2>
        <p class="text-sm text-gray-500 mt-0.5">
          Confirm your scheme membership details and nominate your beneficiaries.
        </p>
      </div>
      <StatusBadge v-if="form.doc" :status="form.doc.status" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-16 text-gray-400">
      <svg class="animate-spin w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      Loading your form…
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="card p-4 border-l-4 border-error text-error text-sm">
      {{ loadError }}
    </div>

    <template v-else>
      <!-- Staff instructions -->
      <div
        v-if="settings.staff_instructions"
        class="card p-4 mb-4 text-sm text-gray-700 prose prose-sm max-w-none"
        v-html="settings.staff_instructions"
      />

      <!-- Enrolment closed -->
      <div v-if="!settings.enrolment_open" class="card p-4 mb-4 border-l-4 border-amber-400 text-sm text-amber-800 bg-amber-50">
        Enrolment is currently closed. You can view your form but cannot submit changes.
      </div>

      <!-- BC unavailable notice -->
      <div v-if="bc.status === 'unavailable'" class="card p-4 mb-4 border-l-4 border-amber-400 text-sm text-amber-800 bg-amber-50">
        {{ bc.error || 'HR records are unreachable right now; you can still fill the form manually.' }}
      </div>

      <!-- Status banner -->
      <div v-if="statusBanner" class="mb-4">
        <div v-if="form.doc?.status === 'Needs More Info'" class="rounded-lg bg-orange-50 border border-orange-200 p-3 text-sm">
          <p class="font-semibold text-orange-800 mb-1">Reviewer Note - more information needed</p>
          <p class="text-orange-700">{{ latestRemark || 'No remark provided.' }}</p>
        </div>
        <div v-else class="rounded-lg bg-blue-50 border border-blue-200 p-3 text-sm text-blue-800 flex items-center justify-between gap-3">
          <span>{{ statusBanner }} ({{ form.doc.name }})</span>
          <button
            v-if="form.can_start_new"
            type="button"
            class="text-xs font-semibold text-primary hover:underline whitespace-nowrap"
            @click="startNew"
          >Fill a new form</button>
        </div>
      </div>

      <div class="card p-5 space-y-6">
        <!-- Section A -->
        <div>
          <h3 class="section-title">Section A: Member &amp; Employment Details</h3>
          <div class="rounded-lg bg-green-50 border border-green-200 p-3 text-xs text-green-800 mb-3">
            Details below are prefilled from your HR record - please confirm they are correct and complete the rest.
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="label">Scheme Name</label>
              <input type="text" class="input-field bg-gray-50" :value="settings.scheme_name" disabled />
            </div>
            <div>
              <label class="label">Member's Full Name <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="state.member_full_name" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Employee Number</label>
              <input type="text" class="input-field bg-gray-50" :value="displayEmployeeNumber" disabled />
            </div>
            <div>
              <label class="label">Department</label>
              <input type="text" class="input-field bg-gray-50" :value="displayDepartment" disabled />
            </div>
            <div>
              <label class="label">Position</label>
              <input type="text" class="input-field" v-model="state.occupation" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Date of Birth <span class="required-asterisk">*</span></label>
              <input type="date" class="input-field" v-model="state.date_of_birth" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Marital Status</label>
              <select class="input-field" v-model="state.marital_status" :disabled="!editable">
                <option value="">Select…</option>
                <option>Single</option><option>Married</option><option>Divorced</option><option>Widowed</option>
              </select>
            </div>
            <div>
              <label class="label">Member Number</label>
              <input type="text" class="input-field" v-model="state.member_number" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Date of Admission to the Scheme</label>
              <input type="date" class="input-field" v-model="state.date_of_admission" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Date of Appointment</label>
              <input type="date" class="input-field" v-model="state.date_of_appointment" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Mobile Number</label>
              <input type="text" class="input-field" v-model="state.mobile_number" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Work Email</label>
              <input type="email" class="input-field bg-gray-50" :value="state.email" disabled />
            </div>
            <div>
              <label class="label">Personal Email <span class="required-asterisk">*</span></label>
              <input type="email" class="input-field" v-model="state.personal_email" :disabled="!editable" />
            </div>
            <div>
              <label class="label">KRA PIN No.</label>
              <input type="text" class="input-field" v-model="state.kra_pin" :disabled="!editable" />
            </div>
            <div>
              <label class="label">ID No. <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="state.id_number" :disabled="!editable" />
            </div>
          </div>
          <label class="flex items-start gap-2 mt-3 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" class="mt-0.5" v-model="state.details_confirmed" :disabled="!editable" />
            I confirm the member details above are correct.
          </label>
        </div>

        <!-- AVC -->
        <div>
          <h3 class="section-title">Additional Voluntary Contributions <span class="text-gray-400 font-normal text-xs">(optional)</span></h3>
          <p class="text-xs text-gray-500 mb-3">
            Deduction from your salary paid to {{ settings.administrator_name || 'the scheme administrator' }} over and above
            your normal monthly contributions. Fill either an amount <em>or</em> a percentage, not both.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="label">Amount (Kshs per month)</label>
              <input type="number" min="0" step="0.01" class="input-field" v-model.number="state.avc_amount" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Percent (% per month)</label>
              <input type="number" min="0" max="100" step="0.01" class="input-field" v-model.number="state.avc_percent" :disabled="!editable" />
            </div>
          </div>
          <p v-if="state.avc_amount && state.avc_percent" class="text-xs text-error mt-1">
            Fill either an amount or a percentage - not both.
          </p>
        </div>

        <!-- Section B -->
        <div>
          <h3 class="section-title">Section B: Bank Details</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="label">Account Name <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="state.bank_account_name" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Bank <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="state.bank_name" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Bank Branch</label>
              <input type="text" class="input-field" v-model="state.bank_branch" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Account Number <span class="required-asterisk">*</span></label>
              <input type="text" class="input-field" v-model="state.bank_account_number" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Town/City</label>
              <input type="text" class="input-field" v-model="state.bank_town_city" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Bank Code</label>
              <input type="text" class="input-field" v-model="state.bank_code" :disabled="!editable" />
            </div>
            <div>
              <label class="label">Branch Code</label>
              <input type="text" class="input-field" v-model="state.branch_code" :disabled="!editable" />
            </div>
            <div>
              <label class="label">SWIFT Code</label>
              <input type="text" class="input-field" v-model="state.swift_code" :disabled="!editable" />
            </div>
            <div>
              <label class="label">SORT Code/IBAN Code</label>
              <input type="text" class="input-field" v-model="state.sort_or_iban_code" :disabled="!editable" />
            </div>
          </div>
        </div>

        <!-- Section C -->
        <div>
          <h3 class="section-title">Section C: Beneficiary Nomination</h3>
          <p v-if="settings.nomination_statement" class="text-xs text-gray-600 italic mb-3" v-html="settings.nomination_statement" />
          <BeneficiaryTable
            ref="beneficiaryTable"
            :rows="state.beneficiaries"
            :guardians="state.guardians"
            :editable="editable"
            :suggestions="availableSuggestions"
            @add-suggestion="addSuggestion"
          />
          <p class="text-xs text-gray-500 mt-2">
            NB: If beneficiaries are under 18 years of age, kindly indicate the Birth Certificate No.
          </p>
        </div>

        <!-- Section D -->
        <div>
          <h3 class="section-title">Section D: Member's Declaration</h3>
          <p v-if="settings.declaration_text" class="text-xs text-gray-600 italic mb-2" v-html="settings.declaration_text" />
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-2">
            <div>
              <label class="label">Signed At (Place)</label>
              <input type="text" class="input-field" v-model="state.signed_at" :disabled="!editable" placeholder="e.g. Nairobi" />
            </div>
          </div>
          <label class="flex items-start gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" class="mt-0.5" v-model="state.declaration_accepted" :disabled="!editable" />
            I hereby declare that all statements shared above are complete and true, agree to the Scheme Rules,
            and understand this nomination nullifies any previous nomination I submitted to the scheme trustees.
            <span class="required-asterisk">*</span>
          </label>
          <p class="text-xs text-gray-400 mt-2">
            It is your responsibility to update the Trustees on any changes in the details given above.
          </p>
        </div>

        <!-- Actions -->
        <div v-if="editable" class="flex items-center gap-3 pt-2 border-t border-gray-100">
          <button type="button" class="btn-secondary" :disabled="saving" @click="save(false)">
            Save Draft
          </button>
          <button
            type="button"
            class="btn-primary"
            :disabled="saving || !state.declaration_accepted || !settings.enrolment_open"
            @click="save(true)"
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useApi } from '../composables/useApi.js'
import { useToast } from '../composables/useToast.js'
import StatusBadge from '../components/StatusBadge.vue'
import BeneficiaryTable from '../components/BeneficiaryTable.vue'

const api = useApi()
const toast = useToast()

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const startedNew = ref(false)

const settings = ref({})
const employeePrefill = ref({})
const form = ref({})
const bc = ref({ status: 'skipped', error: '', suggestions: [] })
const beneficiaryTable = ref(null)

const emptyState = () => ({
  member_full_name: '', occupation: '', date_of_birth: '', marital_status: '',
  member_number: '', date_of_admission: '', date_of_appointment: '',
  mobile_number: '', email: '', personal_email: '', kra_pin: '', id_number: '', details_confirmed: false,
  avc_amount: null, avc_percent: null,
  bank_account_name: '', bank_name: '', bank_branch: '', bank_account_number: '',
  bank_town_city: '', bank_code: '', branch_code: '', swift_code: '', sort_or_iban_code: '',
  declaration_accepted: false, signed_at: '',
  beneficiaries: [], guardians: [],
})

const state = reactive(emptyState())

const editable = computed(() => {
  if (startedNew.value) return true
  if (!form.value?.doc) return true
  return ['Draft', 'Needs More Info'].includes(form.value.doc.status)
})

const BANNERS = {
  Submitted: 'Your form has been submitted and is awaiting review. It can no longer be edited.',
  Reviewed: 'Your form has been reviewed and accepted.',
  Rejected: 'Your form was rejected.',
  Superseded: 'This form has been superseded by a newer submission.',
}
const statusBanner = computed(() => {
  const status = form.value?.doc?.status
  if (!status || startedNew.value) return ''
  if (status === 'Needs More Info') return 'nmi'
  return BANNERS[status] || ''
})
const latestRemark = computed(() => {
  const actions = form.value?.doc?.review_actions || []
  return actions.slice().reverse().find((a) => a.action === 'Needs More Info')?.remarks || ''
})

const displayEmployeeNumber = computed(
  () => form.value?.doc?.employee_number || employeePrefill.value.employee_number || ''
)
const displayDepartment = computed(
  () => form.value?.doc?.department || employeePrefill.value.department || ''
)

const availableSuggestions = computed(() => {
  const used = new Set(state.beneficiaries.map((b) => b.bc_relative_no).filter(Boolean))
  return (bc.value.suggestions || []).filter((s) => !s.bc_relative_no || !used.has(s.bc_relative_no))
})

function addSuggestion(s) {
  state.beneficiaries.push({
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
  state.member_full_name = p.employee_name || ''
  state.occupation = p.designation || ''
  state.date_of_birth = p.date_of_birth || ''
  state.date_of_appointment = p.date_of_joining || ''
  state.mobile_number = p.cell_number || ''
  state.email = p.email || ''
  state.personal_email = p.personal_email || ''
}

function prepopulateBeneficiaries() {
  // First time on the form: start the list off with everything HR has on
  // file. Once a doc exists (draft or submitted) we never auto-fill again.
  if (state.beneficiaries.length) return
  ;(bc.value.suggestions || []).forEach(addSuggestion)
}

function hydrate() {
  const doc = form.value?.doc
  if (!doc) {
    applyPrefill()
    prepopulateBeneficiaries()
    return
  }
  Object.keys(state).forEach((field) => {
    if (field === 'beneficiaries' || field === 'guardians') return
    if (doc[field] !== undefined && doc[field] !== null) state[field] = doc[field]
  })
  state.declaration_accepted = Boolean(doc.declaration_accepted)
  state.details_confirmed = Boolean(doc.details_confirmed)
  state.beneficiaries = (doc.beneficiaries || []).map((b) => ({ ...b }))
  state.guardians = (doc.guardians || []).map((g) => ({ ...g }))
}

function startNew() {
  startedNew.value = true
  Object.assign(state, emptyState())
  state.beneficiaries = []
  state.guardians = []
  applyPrefill()
  prepopulateBeneficiaries()
  toast.info('Started a new form - it will replace your previous one when reviewed.')
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.call('onerc_compliance.api.v1.scheme.get_my_form')
    if (res.status !== 'success') {
      loadError.value = res.message || 'Failed to load your form.'
      return
    }
    settings.value = res.data.settings || {}
    employeePrefill.value = res.data.employee_prefill || {}
    form.value = res.data.form || {}
    bc.value = res.data.bc || { status: 'skipped', error: '', suggestions: [] }
    hydrate()
  } catch (e) {
    loadError.value = e.message || 'Failed to load your form.'
  } finally {
    loading.value = false
  }
}

async function save(submit) {
  if (submit) {
    if (!state.beneficiaries.length) {
      toast.error('Add at least one beneficiary before submitting.')
      return
    }
    if (beneficiaryTable.value && !beneficiaryTable.value.totalOk) {
      toast.error('Beneficiary % shares must total exactly 100.')
      return
    }
    if (state.avc_amount && state.avc_percent) {
      toast.error('Additional Voluntary Contributions: fill either an amount or a percentage, not both.')
      return
    }
  }

  saving.value = true
  try {
    const payload = {
      ...state,
      declaration_accepted: state.declaration_accepted ? 1 : 0,
      details_confirmed: state.details_confirmed ? 1 : 0,
    }

    const res = await api.call('onerc_compliance.api.v1.scheme.save_form', {
      payload,
      submit: submit ? 1 : 0,
    })
    if (res.status !== 'success') {
      toast.error(res.message || 'Save failed.')
      return
    }
    startedNew.value = false
    toast.success(submit ? 'Form submitted for review.' : 'Draft saved.')
    await load()
  } catch (e) {
    toast.error(e.message || 'Save failed.')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.section-title {
  @apply text-sm font-bold text-navy mb-2 pb-1 border-b border-gray-100;
}
</style>
