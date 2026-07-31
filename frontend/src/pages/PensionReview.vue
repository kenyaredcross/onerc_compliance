<template>
  <div class="p-6 max-w-5xl mx-auto space-y-6">
    <div>
      <h2 class="text-xl font-bold text-navy">Pension Review</h2>
      <p class="text-sm text-gray-500 mt-0.5">Review pension compliance submissions per employee.</p>
    </div>

    <!-- Filters -->
    <div class="card p-4 flex flex-wrap items-center gap-3">
      <div class="relative flex-1 min-w-[12rem]">
        <svg class="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
          fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z"/>
        </svg>
        <input type="text" class="input-field text-sm pl-9" placeholder="Search by name or staff ID"
          v-model="search" @input="onSearch" />
      </div>
      <select class="input-field text-sm w-44" v-model="statusFilter" @change="load(1)">
        <option value="">All statuses</option>
        <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
      </select>
      <button v-if="search || statusFilter" class="btn-secondary text-xs py-1.5" @click="clearFilters">
        Clear filters
      </button>
      <button class="btn-primary text-xs py-1.5 flex items-center gap-1.5" @click="exportForms">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
        </svg>
        Export
      </button>
    </div>

    <!-- List -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="py-10 text-center text-gray-400 text-sm">Loading…</div>
      <div v-else-if="loadError" class="py-10 text-center text-error text-sm">{{ loadError }}</div>
      <div v-else-if="!rows.length" class="py-10 text-center text-gray-400 text-sm">No records found.</div>
      <div v-else class="divide-y divide-gray-100">

        <div v-for="row in rows" :key="row.name">
          <!-- Row header -->
          <div
            class="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
            @click="toggleRow(row)"
          >
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ row.employee_name || row.name }}</p>
              <p class="text-xs text-gray-500">
                {{ row.employee_number || '' }}{{ row.department ? ' · ' + row.department : '' }}
                <span class="text-gray-300"> · {{ row.name }}</span>
              </p>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <StatusBadge :status="row.status" />
            </div>
            <svg
              class="w-4 h-4 text-gray-300 flex-shrink-0 transition-transform"
              :class="expanded === row.name ? 'rotate-180' : ''"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </div>

          <!-- Expanded detail -->
          <div v-if="expanded === row.name" class="bg-gray-50 border-t border-gray-100 divide-y divide-gray-200">

            <div v-if="detailLoading" class="p-6 text-sm text-gray-400 text-center">Loading detail…</div>

            <!-- ===== EDIT MODE ===== -->
            <template v-else-if="detail && editing">
              <div class="p-5 space-y-5">
                <div class="flex items-center justify-between">
                  <p class="text-xs font-bold text-navy uppercase tracking-wide">Editing {{ detail.name }}</p>
                  <div class="flex gap-2">
                    <button class="btn-secondary text-xs py-1.5" :disabled="savingEdit" @click="cancelEdit">Cancel</button>
                    <button class="btn-primary text-xs py-1.5" :disabled="savingEdit" @click="saveEdit">
                      {{ savingEdit ? 'Saving…' : 'Save Changes' }}
                    </button>
                  </div>
                </div>

                <div>
                  <p class="text-xs font-semibold text-gray-500 mb-2">Member &amp; Employment Details</p>
                  <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div v-for="f in memberEditFields" :key="f.key">
                      <label class="label">{{ f.label }}</label>
                      <select v-if="f.type === 'select'" class="input-field text-sm" v-model="editDraft[f.key]">
                        <option value=""></option>
                        <option v-for="o in f.options" :key="o">{{ o }}</option>
                      </select>
                      <input v-else :type="f.type || 'text'" class="input-field text-sm" v-model="editDraft[f.key]" />
                    </div>
                  </div>
                </div>

                <div>
                  <p class="text-xs font-semibold text-gray-500 mb-2">Bank Details</p>
                  <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div v-for="f in bankEditFields" :key="f.key">
                      <label class="label">{{ f.label }}</label>
                      <input type="text" class="input-field text-sm" v-model="editDraft[f.key]" />
                    </div>
                  </div>
                </div>

                <div>
                  <div class="flex items-center justify-between mb-2">
                    <p class="text-xs font-semibold text-gray-500">Beneficiaries</p>
                    <button class="text-xs font-medium text-primary hover:underline" @click="addEditBeneficiary">+ Add</button>
                  </div>
                  <div v-for="(b, i) in editDraft.beneficiaries" :key="i" class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-2 p-2 rounded border border-gray-200 bg-white">
                    <input type="text" class="input-field text-sm" placeholder="Name" v-model="b.full_name" />
                    <input type="text" class="input-field text-sm" placeholder="Relationship" v-model="b.relationship" />
                    <input type="date" class="input-field text-sm" v-model="b.date_of_birth" />
                    <input type="text" class="input-field text-sm" placeholder="ID No." v-model="b.id_number" />
                    <input type="text" class="input-field text-sm" placeholder="Birth Cert No." v-model="b.birth_certificate_no" />
                    <input type="text" class="input-field text-sm" placeholder="Mobile" v-model="b.mobile" />
                    <input type="number" min="0" max="100" step="0.01" class="input-field text-sm" placeholder="% Share" v-model.number="b.share_percent" />
                    <button class="text-xs text-error hover:underline text-left" @click="editDraft.beneficiaries.splice(i, 1)">Remove</button>
                  </div>
                  <p class="text-xs" :class="editTotalOk ? 'text-green-700' : 'text-error'">
                    Total allocation: {{ editTotal.toFixed(2) }}% {{ editTotalOk ? '✓' : '(must equal 100%)' }}
                  </p>
                </div>

                <div>
                  <div class="flex items-center justify-between mb-2">
                    <p class="text-xs font-semibold text-gray-500">Guardians</p>
                    <button class="text-xs font-medium text-primary hover:underline" @click="addEditGuardian">+ Add</button>
                  </div>
                  <div v-for="(g, i) in editDraft.guardians" :key="i" class="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-2 p-2 rounded border border-gray-200 bg-white">
                    <input type="text" class="input-field text-sm" placeholder="Guardian Name" v-model="g.guardian_name" />
                    <select class="input-field text-sm" v-model="g.beneficiary_name">
                      <option value="" disabled>Guardian of…</option>
                      <option v-for="n in editBeneficiaryNames" :key="n" :value="n">{{ n }}</option>
                    </select>
                    <input type="text" class="input-field text-sm" placeholder="Relationship to Beneficiary" v-model="g.relationship_to_beneficiary" />
                    <input type="text" class="input-field text-sm" placeholder="ID No." v-model="g.id_number" />
                    <input type="text" class="input-field text-sm" placeholder="Mobile" v-model="g.mobile" />
                    <button class="text-xs text-error hover:underline text-left" @click="editDraft.guardians.splice(i, 1)">Remove</button>
                  </div>
                </div>
              </div>
            </template>

            <!-- ===== VIEW MODE ===== -->
            <template v-else-if="detail">

              <!-- PART 1: MEMBER & EMPLOYMENT DETAILS -->
              <div class="p-5 space-y-3">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Part 1: Member &amp; Employment Details</p>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  <div><span class="text-gray-400 text-xs block">Full Name</span>{{ detail.member_full_name || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Employee Number</span>{{ detail.employee_number || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Department</span>{{ detail.department || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Position</span>{{ detail.occupation || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">ID No.</span>{{ detail.id_number || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">KRA PIN</span>{{ detail.kra_pin || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Work Email</span>{{ detail.email || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Personal Email</span>{{ detail.personal_email || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Mobile</span>{{ detail.mobile_number || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Marital Status</span>{{ detail.marital_status || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Date of Birth</span>{{ detail.date_of_birth || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Member Number</span>{{ detail.member_number || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Date of Admission</span>{{ detail.date_of_admission || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Date of Appointment</span>{{ detail.date_of_appointment || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Scheme Name</span>{{ detail.scheme_name || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Signed At</span>{{ detail.signed_at || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Data Consent</span>{{ detail.data_consent || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Marketing Consent</span>{{ detail.marketing_consent || '-' }}</div>
                </div>
              </div>

              <!-- PART 2: BANK DETAILS -->
              <div class="p-5 space-y-3">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Part 2: Bank Details</p>
                <div v-if="!detail.bank_name && !detail.bank_account_number" class="text-sm text-gray-400 italic">Not provided.</div>
                <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  <div><span class="text-gray-400 text-xs block">Account Name</span>{{ detail.bank_account_name || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Bank</span>{{ detail.bank_name || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Account No.</span>{{ detail.bank_account_number || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Branch</span>{{ detail.bank_branch || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Bank Code</span>{{ detail.bank_code || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">Branch Code</span>{{ detail.branch_code || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">SWIFT Code</span>{{ detail.swift_code || '-' }}</div>
                  <div><span class="text-gray-400 text-xs block">SORT/IBAN</span>{{ detail.sort_or_iban_code || '-' }}</div>
                </div>
              </div>

              <!-- PART 3: AVC -->
              <div v-if="detail.avc_amount || detail.avc_percent" class="p-5 space-y-2">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Part 3: Additional Voluntary Contributions</p>
                <div class="grid grid-cols-2 gap-3 text-sm">
                  <div v-if="detail.avc_amount"><span class="text-gray-400 text-xs block">Amount (Kshs/month)</span>{{ detail.avc_amount }}</div>
                  <div v-if="detail.avc_percent"><span class="text-gray-400 text-xs block">Percent (%/month)</span>{{ detail.avc_percent }}%</div>
                </div>
              </div>

              <!-- PART 4: BENEFICIARY NOMINATION -->
              <div class="p-5 space-y-3">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Part 4: Beneficiary Nomination</p>
                <div v-if="!detail.beneficiaries?.length" class="text-sm text-gray-400 italic">No beneficiaries recorded.</div>
                <div v-else class="rounded-lg border border-gray-200 overflow-hidden">
                  <table class="data-table text-sm w-full">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Relationship</th>
                        <th>Date of Birth</th>
                        <th>ID / Cert No.</th>
                        <th>Source</th>
                        <th class="text-right">% Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(b, i) in detail.beneficiaries" :key="i">
                        <td class="font-medium">{{ b.full_name }}</td>
                        <td>{{ b.relationship }}</td>
                        <td>{{ b.date_of_birth || '-' }}</td>
                        <td>{{ b.id_number || b.birth_certificate_no || '-' }}</td>
                        <td class="text-gray-400">{{ b.source === 'Business Central' ? 'HR records' : 'Member' }}</td>
                        <td class="text-right">{{ b.share_percent }}%</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="detail.guardians?.length" class="space-y-1">
                  <p class="text-xs font-semibold text-gray-500 mt-2">Guardians</p>
                  <div v-for="(g, i) in detail.guardians" :key="i" class="text-sm text-gray-700">
                    <span class="font-medium">{{ g.guardian_name }}</span> - guardian of
                    <span class="font-medium">{{ g.beneficiary_name }}</span> · {{ g.relationship_to_beneficiary }}
                    <template v-if="g.id_number"> · ID {{ g.id_number }}</template>
                  </div>
                </div>
              </div>

              <!-- REVIEW -->
              <div class="p-5 space-y-4">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Review</p>

                <div class="space-y-2">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-xs font-semibold text-gray-600">Pension Compliance Form</span>
                    <StatusBadge :status="detail.status" />
                    <span class="text-xs text-gray-400">{{ detail.name }}</span>
                    <span v-if="detail.amends" class="text-xs text-gray-400">(amends {{ detail.amends }})</span>
                    <div class="flex items-center gap-2 ml-auto">
                      <button
                        type="button"
                        class="btn-secondary text-xs py-1"
                        @click="startEdit"
                      >Edit</button>
                      <button
                        type="button"
                        class="btn-secondary text-xs py-1"
                        @click="exportMembershipForm(detail.name)"
                      >Download Jubilee Form (PDF)</button>
                    </div>
                  </div>
                  <div v-if="detail.review_actions?.length" class="space-y-1">
                    <div v-for="(act, i) in detail.review_actions" :key="i" class="flex flex-wrap gap-2 text-xs items-center text-gray-600">
                      <StatusBadge :status="act.action" />
                      <span>by {{ act.reviewer }}</span>
                      <span v-if="act.action_on" class="text-gray-400">{{ formatDate(act.action_on) }}</span>
                      <span v-if="act.remarks" class="italic">- {{ act.remarks }}</span>
                    </div>
                  </div>
                  <div v-if="detail.trustee_1_name || detail.trustee_2_name" class="text-xs text-gray-600">
                    Trustees:
                    <span v-if="detail.trustee_1_name" class="font-medium">{{ detail.trustee_1_name }}</span>
                    <span v-if="detail.trustee_2_name" class="font-medium"> · {{ detail.trustee_2_name }}</span>
                  </div>
                  <ReviewPanel
                    v-if="detail.status === 'Submitted'"
                    :name="detail.name"
                    @done="onReviewDone(row)"
                  />

                  <!-- Trustee approval: Reviewed forms, Pension Trustee only -->
                  <div v-if="detail.status === 'Reviewed'" class="mt-2">
                    <div v-if="auth.isTrustee" class="rounded-lg border border-emerald-200 bg-emerald-50 p-3 space-y-2">
                      <p class="text-xs font-semibold text-emerald-800">
                        Trustee approval - approving sends the notification email with the Jubilee PDF attached.
                      </p>
                      <textarea
                        class="input-field resize-none text-sm"
                        rows="2"
                        placeholder="Remarks (optional)"
                        v-model="approveRemarks"
                      />
                      <button class="btn-primary text-xs !bg-emerald-600 hover:!bg-emerald-700" :disabled="approving" @click="approve">
                        {{ approving ? 'Approving…' : 'Approve' }}
                      </button>
                    </div>
                    <p v-else class="text-xs text-gray-400 italic">
                      Awaiting approval by a Pension Trustee.
                    </p>
                  </div>
                </div>
              </div>

            </template>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="!loading && rows.length" class="px-4 py-3 border-t border-gray-100 flex items-center justify-between gap-3 flex-wrap">
        <p class="text-xs text-gray-500">Showing {{ rows.length }} of {{ totalCount }}</p>
        <div v-if="totalPages > 1" class="flex items-center gap-2">
          <button class="btn-secondary text-xs py-1.5" :disabled="page <= 1" @click="load(page - 1)">Previous</button>
          <span class="text-xs text-gray-500">Page {{ page }} of {{ totalPages }}</span>
          <button class="btn-secondary text-xs py-1.5" :disabled="page >= totalPages" @click="load(page + 1)">Next</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import { useApi } from '../composables/useApi.js'
import { useToast } from '../composables/useToast.js'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuthStore } from '../stores/auth.js'

const api = useApi()
const toast = useToast()
const auth = useAuthStore()

const statuses = ['Draft', 'Submitted', 'Needs More Info', 'Reviewed', 'Approved', 'Rejected', 'Superseded']

const loading = ref(false)
const loadError = ref('')
const rows = ref([])
const totalCount = ref(0)
const page = ref(1)
const PAGE_LENGTH = 25
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / PAGE_LENGTH)))

const search = ref('')
const statusFilter = ref('Submitted')

const expanded = ref(null)
const detail = ref(null)
const detailLoading = ref(false)

// ---- Officer edit mode ----
const editing = ref(false)
const savingEdit = ref(false)
const editDraft = ref(null)

const memberEditFields = [
  { key: 'member_full_name', label: 'Full Name' },
  { key: 'occupation', label: 'Position' },
  { key: 'date_of_birth', label: 'Date of Birth', type: 'date' },
  { key: 'marital_status', label: 'Marital Status', type: 'select', options: ['Single', 'Married', 'Divorced', 'Widowed'] },
  { key: 'id_number', label: 'ID No.' },
  { key: 'kra_pin', label: 'KRA PIN' },
  { key: 'email', label: 'Work Email' },
  { key: 'personal_email', label: 'Personal Email' },
  { key: 'mobile_number', label: 'Mobile' },
  { key: 'member_number', label: 'Member Number' },
  { key: 'date_of_admission', label: 'Date of Admission', type: 'date' },
  { key: 'date_of_appointment', label: 'Date of Appointment', type: 'date' },
  { key: 'signed_at', label: 'Signed At' },
  { key: 'data_consent', label: 'Data Consent', type: 'select', options: ['I Consent', 'I Do Not Consent'] },
  { key: 'marketing_consent', label: 'Marketing Consent', type: 'select', options: ['I Consent', 'I Do Not Consent'] },
  { key: 'avc_amount', label: 'AVC Amount (Kshs)', type: 'number' },
  { key: 'avc_percent', label: 'AVC Percent', type: 'number' },
]
const bankEditFields = [
  { key: 'bank_account_name', label: 'Account Name' },
  { key: 'bank_name', label: 'Bank' },
  { key: 'bank_branch', label: 'Bank Branch' },
  { key: 'bank_account_number', label: 'Account Number' },
  { key: 'bank_town_city', label: 'Town/City' },
  { key: 'bank_code', label: 'Bank Code' },
  { key: 'branch_code', label: 'Branch Code' },
  { key: 'swift_code', label: 'SWIFT Code' },
  { key: 'sort_or_iban_code', label: 'SORT/IBAN Code' },
]

const editTotal = computed(() =>
  (editDraft.value?.beneficiaries || []).reduce((sum, b) => sum + (Number(b.share_percent) || 0), 0)
)
const editTotalOk = computed(() => Math.abs(editTotal.value - 100) <= 0.01)
const editBeneficiaryNames = computed(() =>
  (editDraft.value?.beneficiaries || []).map((b) => (b.full_name || '').trim()).filter(Boolean)
)

function startEdit() {
  editDraft.value = {
    ...detail.value,
    beneficiaries: (detail.value.beneficiaries || []).map((b) => ({ ...b })),
    guardians: (detail.value.guardians || []).map((g) => ({ ...g })),
  }
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  editDraft.value = null
}

function addEditBeneficiary() {
  editDraft.value.beneficiaries.push({
    full_name: '', email: '', mobile: '', date_of_birth: '', id_number: '',
    birth_certificate_no: '', relationship: '', share_percent: null,
    source: 'Manual', bc_relative_no: '', bc_line_no: 0, bc_category: '',
  })
}

function addEditGuardian() {
  editDraft.value.guardians.push({
    guardian_name: '', email: '', mobile: '', id_number: '',
    beneficiary_name: '', relationship_to_beneficiary: '',
  })
}

async function saveEdit() {
  if (editDraft.value.beneficiaries.length && !editTotalOk.value) {
    toast.error('Beneficiary % shares must total exactly 100.')
    return
  }
  savingEdit.value = true
  try {
    const res = await api.call('onerc_compliance.api.v1.scheme.officer_update_form', {
      name: editDraft.value.name,
      payload: editDraft.value,
    })
    if (res.status !== 'success') { toast.error(res.message || 'Save failed.'); return }
    detail.value = res.data
    editing.value = false
    editDraft.value = null
    toast.success('Changes saved.')
    await load(page.value)
    expanded.value = detail.value.name
  } catch (e) {
    toast.error(e.message || 'Save failed.')
  } finally {
    savingEdit.value = false
  }
}

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => load(1), 350)
}

function clearFilters() {
  search.value = ''
  statusFilter.value = ''
  load(1)
}

async function load(p = 1) {
  page.value = p
  loading.value = true
  loadError.value = ''
  expanded.value = null
  detail.value = null

  try {
    const res = await api.call('onerc_compliance.api.v1.scheme.get_forms', {
      status: statusFilter.value || undefined,
      search: search.value || undefined,
      page: p,
      page_length: PAGE_LENGTH,
    })
    if (res.status !== 'success') { loadError.value = res.message || 'Failed to load.'; return }
    rows.value = res.data
    totalCount.value = res.meta?.total_count ?? res.data.length
  } catch (e) {
    loadError.value = e.message || 'Failed to load.'
  } finally {
    loading.value = false
  }
}

async function toggleRow(row) {
  editing.value = false
  editDraft.value = null
  if (expanded.value === row.name) {
    expanded.value = null
    detail.value = null
    return
  }
  expanded.value = row.name
  detail.value = null
  detailLoading.value = true
  try {
    const res = await api.call('onerc_compliance.api.v1.scheme.get_form_detail', { name: row.name })
    if (res.status === 'success') detail.value = res.data
    else toast.error(res.message || 'Failed to load detail.')
  } catch (e) {
    toast.error(e.message || 'Failed to load detail.')
  } finally {
    detailLoading.value = false
  }
}

async function onReviewDone(row) {
  await toggleRow(row)   // collapse
  await load(page.value) // refresh list
  const fresh = rows.value.find((r) => r.name === row.name)
  if (fresh) await toggleRow(fresh) // re-expand with fresh data
}

async function exportMembershipForm(name) {
  // Download the filled Jubilee Membership Application Form as a PDF.
  try {
    const res = await fetch(
      `/api/method/onerc_compliance.api.v1.scheme.export_membership_form?name=${encodeURIComponent(name)}&as_pdf=1`
    )
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const buf = await res.arrayBuffer()
    const url = URL.createObjectURL(new Blob([buf], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `${name}_membership_application.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error(e.message || 'Download failed.')
  }
}

function exportForms() {
  // Excel download of all forms matching the current filters (all statuses
  // when no status filter is set). Session cookie authenticates the request.
  const params = new URLSearchParams()
  if (statusFilter.value) params.set('status', statusFilter.value)
  if (search.value.trim()) params.set('search', search.value.trim())
  window.open(`/api/method/onerc_compliance.api.v1.scheme.export_forms?${params.toString()}`, '_blank')
}

function formatDate(val) {
  if (!val) return '-'
  return new Date(val).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

// ---- Trustee approval ----
const approveRemarks = ref('')
const approving = ref(false)

async function approve() {
  approving.value = true
  try {
    const res = await api.call('onerc_compliance.api.v1.scheme.review_form', {
      name: detail.value.name,
      action: 'Approved',
      remarks: approveRemarks.value || '',
    })
    if (res.status !== 'success') { toast.error(res.message || 'Approval failed.'); return }
    toast.success('Form approved - notification email with the Jubilee PDF is being sent.')
    approveRemarks.value = ''
    const row = rows.value.find((r) => r.name === detail.value.name)
    if (row) await onReviewDone(row)
  } catch (e) {
    toast.error(e.message || 'Approval failed.')
  } finally {
    approving.value = false
  }
}

// Inline review panel component
const ReviewPanel = defineComponent({
  props: { name: String },
  emits: ['done'],
  setup(props, { emit }) {
    const action = ref(null)
    const remarks = ref('')
    const busy = ref(false)
    const canConfirm = computed(() =>
      action.value && (action.value === 'Reviewed' || remarks.value.trim().length > 0)
    )
    async function confirm() {
      if (!canConfirm.value) return
      busy.value = true
      try {
        const res = await api.call('onerc_compliance.api.v1.scheme.review_form', {
          name: props.name,
          action: action.value,
          remarks: remarks.value || '',
        })
        if (res.status !== 'success') { toast.error(res.message || 'Review failed.'); return }
        toast.success(`Marked as ${action.value}.`)
        action.value = null
        remarks.value = ''
        emit('done')
      } catch (e) {
        toast.error(e.message || 'Review failed.')
      } finally {
        busy.value = false
      }
    }
    return () => {
      if (!action.value) {
        return h('div', { class: 'flex gap-2 flex-wrap mt-2' }, [
          h('button', { class: 'btn-success text-xs', onClick: () => { action.value = 'Reviewed'; remarks.value = '' } }, 'Mark Reviewed'),
          h('button', { class: 'btn-warning text-xs', onClick: () => { action.value = 'Needs More Info'; remarks.value = '' } }, 'Needs More Info'),
          h('button', { class: 'btn-danger text-xs', onClick: () => { action.value = 'Rejected'; remarks.value = '' } }, 'Reject'),
        ])
      }
      return h('div', { class: 'space-y-2 mt-2' }, [
        action.value !== 'Reviewed'
          ? h('textarea', {
              class: 'input-field resize-none text-sm',
              rows: 2,
              placeholder: `Remarks required for ${action.value}`,
              value: remarks.value,
              onInput: (e) => { remarks.value = e.target.value },
            })
          : h('p', { class: 'text-xs text-gray-500' }, 'Confirm marking as Reviewed. Remarks optional.'),
        h('div', { class: 'flex gap-2' }, [
          h('button', { class: 'btn-primary text-xs', disabled: !canConfirm.value || busy.value, onClick: confirm },
            busy.value ? 'Processing…' : `Confirm ${action.value}`),
          h('button', { class: 'btn-secondary text-xs', onClick: () => { action.value = null } }, 'Cancel'),
        ]),
      ])
    }
  },
})

onMounted(() => load(1))
</script>
