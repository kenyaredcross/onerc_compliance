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
      <!-- Staff instructions -->
      <div
        v-if="settings.staff_instructions"
        class="card p-4 mb-4 text-sm text-gray-700 prose prose-sm max-w-none"
        v-html="settings.staff_instructions"
      />

      <!-- Enrolment closed -->
      <div v-if="!settings.enrolment_open" class="card p-4 mb-4 border-l-4 border-amber-400 text-sm text-amber-800 bg-amber-50">
        Enrolment is currently closed. You can view your forms but cannot submit changes.
      </div>

      <!-- BC unavailable notice -->
      <div v-if="bc.status === 'unavailable'" class="card p-4 mb-4 border-l-4 border-amber-400 text-sm text-amber-800 bg-amber-50">
        {{ bc.error || 'HR records are unreachable right now; you can still fill the forms manually.' }}
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 mb-4 border-b border-gray-200">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border"
          :class="activeTab === tab.key
            ? 'bg-white border-gray-200 border-b-white text-navy'
            : 'bg-transparent border-transparent text-gray-500 hover:text-navy'"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <StatusBadge v-if="formStatus(tab.key)" :status="formStatus(tab.key)" class="ml-1.5" />
        </button>
      </div>

      <!-- ============ OCCUPATIONAL SCHEME FORM ============ -->
      <div v-show="activeTab === 'scheme'" class="space-y-4">
        <FormStateBanner :form="forms.scheme" @start-new="startNew('scheme')" />

        <div class="card p-5 space-y-5">
          <!-- Section A -->
          <div>
            <h3 class="section-title">Section A — Employment Details</h3>
            <div class="rounded-lg bg-green-50 border border-green-200 p-3 text-xs text-green-800 mb-3">
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
            </MemberBasicInfo>
            <label class="flex items-start gap-2 mt-3 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" class="mt-0.5" v-model="scheme.details_confirmed" :disabled="!schemeEditable" />
              I confirm the employment details above are correct.
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
                <input type="number" min="0" step="0.01" class="input-field" v-model.number="scheme.avc_amount" :disabled="!schemeEditable" />
              </div>
              <div>
                <label class="label">Percent (% per month)</label>
                <input type="number" min="0" max="100" step="0.01" class="input-field" v-model.number="scheme.avc_percent" :disabled="!schemeEditable" />
              </div>
            </div>
            <p v-if="scheme.avc_amount && scheme.avc_percent" class="text-xs text-error mt-1">
              Fill either an amount or a percentage — not both.
            </p>
          </div>

          <!-- Section B -->
          <div>
            <h3 class="section-title">Section B — Bank Details</h3>
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

          <!-- Beneficiaries are nominated in the Beneficiary Nomination form -->
          <div class="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-800">
            Beneficiary nomination is done under the
            <button type="button" class="font-semibold underline" @click="activeTab = 'nomination'">Beneficiary Nomination</button>
            tab.
          </div>

          <!-- Declaration -->
          <div>
            <h3 class="section-title">Declaration</h3>
            <p v-if="settings.declaration_text" class="text-xs text-gray-600 italic mb-2" v-html="settings.declaration_text" />
            <label class="flex items-start gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" class="mt-0.5" v-model="scheme.declaration_accepted" :disabled="!schemeEditable" />
              I hereby declare that all statements and answers above are complete and true, and I agree to the Scheme Rules.
              <span class="required-asterisk">*</span>
            </label>
          </div>

          <!-- Actions -->
          <div v-if="schemeEditable" class="flex items-center gap-3 pt-2 border-t border-gray-100">
            <button type="button" class="btn-secondary" :disabled="saving" @click="save('scheme', false)">
              Save Draft
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="saving || !scheme.declaration_accepted || !settings.enrolment_open"
              @click="save('scheme', true)"
            >
              Submit
            </button>
            <span v-if="saving" class="text-xs text-gray-400">Saving…</span>
          </div>
        </div>
      </div>

      <!-- ============ BENEFICIARY NOMINATION ============ -->
      <div v-show="activeTab === 'nomination'" class="space-y-4">
        <FormStateBanner :form="forms.nomination" @start-new="startNew('nomination')" />

        <div class="card p-5 space-y-5">
          <!-- Section A -->
          <div>
            <h3 class="section-title">Section A — Member Details</h3>
            <div class="rounded-lg bg-green-50 border border-green-200 p-3 text-xs text-green-800 mb-3">
              Details below are prefilled from your HR record — please confirm they are correct.
            </div>
            <MemberBasicInfo :model-value="nomination" :scheme-name="settings.scheme_name" :editable="nominationEditable">
              <div>
                <label class="label">Marital Status</label>
                <select class="input-field" v-model="nomination.marital_status" :disabled="!nominationEditable">
                  <option value="">Select…</option>
                  <option>Single</option><option>Married</option><option>Divorced</option><option>Widowed</option>
                </select>
              </div>
            </MemberBasicInfo>
          </div>

          <!-- Section B -->
          <div>
            <h3 class="section-title">Section B — Beneficiary Details</h3>
            <p v-if="settings.nomination_statement" class="text-xs text-gray-600 italic mb-3" v-html="settings.nomination_statement" />
            <BeneficiaryTable
              ref="nominationTable"
              :rows="nomination.beneficiaries"
              :guardians="nomination.guardians"
              :editable="nominationEditable"
              :suggestions="availableSuggestions('nomination')"
              @add-suggestion="addSuggestion('nomination', $event)"
            />
            <p class="text-xs text-gray-500 mt-2">
              NB: If beneficiaries are under 18 years of age, kindly indicate the Birth Certificate No.
            </p>
          </div>

          <!-- Section C -->
          <div>
            <h3 class="section-title">Section C — Member's Declaration</h3>
            <p v-if="settings.declaration_text" class="text-xs text-gray-600 italic mb-2" v-html="settings.declaration_text" />
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-2">
              <div>
                <label class="label">Signed At (Place)</label>
                <input type="text" class="input-field" v-model="nomination.signed_at" :disabled="!nominationEditable" placeholder="e.g. Nairobi" />
              </div>
            </div>
            <label class="flex items-start gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" class="mt-0.5" v-model="nomination.declaration_accepted" :disabled="!nominationEditable" />
              I hereby declare that all statements shared above are complete and true, that they form part of my application
              for membership, and I agree to the Scheme Rules. I understand this nomination nullifies any previous nomination
              I completed and submitted to the scheme trustees. <span class="required-asterisk">*</span>
            </label>
            <p class="text-xs text-gray-400 mt-2">
              It is your responsibility to update the Trustees on any changes in the details given above.
            </p>
          </div>

          <!-- Actions -->
          <div v-if="nominationEditable" class="flex items-center gap-3 pt-2 border-t border-gray-100">
            <button type="button" class="btn-secondary" :disabled="saving" @click="save('nomination', false)">
              Save Draft
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="saving || !nomination.declaration_accepted || !settings.enrolment_open"
              @click="save('nomination', true)"
            >
              Submit
            </button>
            <span v-if="saving" class="text-xs text-gray-400">Saving…</span>
          </div>
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
const activeTab = ref('scheme')

const tabs = [
  { key: 'scheme', label: 'Occupational Scheme Details' },
  { key: 'nomination', label: 'Beneficiary Nomination' },
]

const settings = ref({})
const employeePrefill = ref({})
const forms = ref({ scheme: {}, nomination: {} })
const bc = ref({ status: 'skipped', error: '', suggestions: [] })
const startedNew = reactive({ scheme: false, nomination: false })

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

// Inline component: banner showing current form state / start-new option
const FormStateBanner = {
  props: ['form'],
  emits: ['start-new'],
  setup(props, { emit }) {
    return () => {
      const doc = props.form?.doc
      if (!doc) return null
      const status = doc.status
      const messages = {
        Submitted: 'This form has been submitted and is awaiting review. It can no longer be edited.',
        Reviewed: 'This form has been reviewed and accepted.',
        Rejected: 'This form was rejected.',
        Superseded: 'This form has been superseded by a newer submission.',
        'Needs More Info': null,
      }
      const children = []
      if (status === 'Needs More Info') {
        const remark = (doc.review_actions || []).slice().reverse().find((a) => a.action === 'Needs More Info')
        children.push(
          h('div', { class: 'rounded-lg bg-orange-50 border border-orange-200 p-3 text-sm' }, [
            h('p', { class: 'font-semibold text-orange-800 mb-1' }, 'Reviewer Note — more information needed'),
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
      return children.length ? h('div', { class: 'space-y-2' }, children) : null
    }
  },
}

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

function formStatus(key) {
  return forms.value[key]?.doc?.status || ''
}

function targetState(key) {
  return key === 'scheme' ? scheme : nomination
}

function availableSuggestions(key) {
  const state = targetState(key)
  const used = new Set(state.beneficiaries.map((b) => b.bc_relative_no).filter(Boolean))
  return (bc.value.suggestions || []).filter((s) => !s.bc_relative_no || !used.has(s.bc_relative_no))
}

function addSuggestion(key, s) {
  targetState(key).beneficiaries.push({
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

function applyPrefill(key) {
  const p = employeePrefill.value
  if (key === 'scheme') {
    scheme.member_full_name = p.employee_name || ''
    scheme.occupation = p.designation || ''
    scheme.date_of_birth = p.date_of_birth || ''
    scheme.date_of_appointment = p.date_of_joining || ''
    scheme.mobile_number = p.cell_number || ''
    scheme.email = p.email || ''
  } else {
    nomination.member_full_name = p.employee_name || ''
    nomination.email = p.email || ''
    nomination.telephone = p.cell_number || ''
  }
}

function prepopulateBeneficiaries(key) {
  // Beneficiaries live on the Beneficiary Nomination form only.
  if (key !== 'nomination') return
  // First time on the form: start the list off with everything HR has on
  // file. The member can remove rows or add more; once a doc exists (draft
  // or submitted) we never auto-fill again.
  const state = targetState(key)
  if (state.beneficiaries.length) return
  ;(bc.value.suggestions || []).forEach((s) => addSuggestion(key, s))
}

function hydrate(key) {
  const doc = forms.value[key]?.doc
  const state = targetState(key)
  if (!doc) {
    applyPrefill(key)
    prepopulateBeneficiaries(key)
    return
  }
  Object.keys(state).forEach((field) => {
    if (field === 'beneficiaries' || field === 'guardians') return
    if (doc[field] !== undefined && doc[field] !== null) state[field] = doc[field]
  })
  state.declaration_accepted = Boolean(doc.declaration_accepted)
  if (key === 'scheme') state.details_confirmed = Boolean(doc.details_confirmed)
  state.beneficiaries = (doc.beneficiaries || []).map((b) => ({ ...b }))
  state.guardians = (doc.guardians || []).map((g) => ({ ...g }))
}

function startNew(key) {
  startedNew[key] = true
  const fresh = key === 'scheme' ? emptyScheme() : emptyNomination()
  Object.assign(targetState(key), fresh)
  applyPrefill(key)
  prepopulateBeneficiaries(key)
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
    hydrate('scheme')
    hydrate('nomination')
  } catch (e) {
    loadError.value = e.message || 'Failed to load your forms.'
  } finally {
    loading.value = false
  }
}

async function save(key, submit) {
  const state = targetState(key)

  if (submit) {
    if (key === 'nomination') {
      if (!state.beneficiaries.length) {
        toast.error('Add at least one beneficiary before submitting.')
        return
      }
      if (nominationTable.value && !nominationTable.value.totalOk) {
        toast.error('Beneficiary % shares must total exactly 100.')
        return
      }
    }
    if (key === 'scheme' && state.avc_amount && state.avc_percent) {
      toast.error('Additional Voluntary Contributions: fill either an amount or a percentage, not both.')
      return
    }
  }

  saving.value = true
  try {
    const payload = { ...state, declaration_accepted: state.declaration_accepted ? 1 : 0 }
    if (key === 'scheme') payload.details_confirmed = state.details_confirmed ? 1 : 0

    const res = await api.call('onerc_compliance.api.v1.scheme.save_form', {
      form_type: key,
      payload,
      submit: submit ? 1 : 0,
    })
    if (res.status !== 'success') {
      toast.error(res.message || 'Save failed.')
      return
    }
    startedNew[key] = false
    toast.success(submit ? 'Form submitted for review.' : 'Draft saved.')
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
  @apply text-sm font-bold text-navy mb-2 pb-1 border-b border-gray-100;
}
</style>
