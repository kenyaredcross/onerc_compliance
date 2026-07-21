<template>
  <div class="p-6 max-w-5xl mx-auto space-y-6">
    <div>
      <h2 class="text-xl font-bold text-navy">Pension Review</h2>
      <p class="text-sm text-gray-500 mt-0.5">Review pension submissions per employee — scheme form and beneficiary nomination together.</p>
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
    </div>

    <!-- List -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="py-10 text-center text-gray-400 text-sm">Loading…</div>
      <div v-else-if="loadError" class="py-10 text-center text-error text-sm">{{ loadError }}</div>
      <div v-else-if="!rows.length" class="py-10 text-center text-gray-400 text-sm">No records found.</div>
      <div v-else class="divide-y divide-gray-100">

        <div v-for="row in rows" :key="row.employee">
          <!-- Row header -->
          <div
            class="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
            @click="toggleRow(row)"
          >
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ row.employee_name || row.employee }}</p>
              <p class="text-xs text-gray-500">
                {{ row.employee_number || '' }}{{ row.department ? ' · ' + row.department : '' }}
              </p>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <span class="text-xs text-gray-400">Scheme:</span>
              <StatusBadge :status="row.scheme_status || 'None'" />
              <span class="text-xs text-gray-400 ml-1">Nomination:</span>
              <StatusBadge :status="row.nomination_status || 'None'" />
            </div>
            <svg
              class="w-4 h-4 text-gray-300 flex-shrink-0 transition-transform"
              :class="expanded === row.employee ? 'rotate-180' : ''"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </div>

          <!-- Expanded detail -->
          <div v-if="expanded === row.employee" class="bg-gray-50 border-t border-gray-100 divide-y divide-gray-200">

            <div v-if="detailLoading" class="p-6 text-sm text-gray-400 text-center">Loading detail…</div>
            <template v-else-if="detail">

              <!-- ── PART 1: EMPLOYMENT DETAILS ── -->
              <div class="p-5 space-y-3">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Part 1 — Employment Details</p>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  <div><span class="text-gray-400 text-xs block">Full Name</span>{{ detail.scheme?.member_full_name || detail.nomination?.member_full_name || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">ID No.</span>{{ detail.scheme?.id_number || detail.nomination?.id_number || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">KRA PIN</span>{{ detail.scheme?.kra_pin || detail.nomination?.kra_pin || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Email</span>{{ detail.scheme?.email || detail.nomination?.email || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Mobile / Tel</span>{{ detail.scheme?.mobile_number || detail.nomination?.telephone || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Marital Status</span>{{ detail.nomination?.marital_status || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Occupation</span>{{ detail.scheme?.occupation || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Date of Birth</span>{{ detail.scheme?.date_of_birth || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Member Number</span>{{ detail.scheme?.member_number || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Date of Admission</span>{{ detail.scheme?.date_of_admission || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Date of Appointment</span>{{ detail.scheme?.date_of_appointment || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Scheme Name</span>{{ detail.scheme?.scheme_name || '—' }}</div>
                </div>
              </div>

              <!-- ── PART 2: BANK DETAILS ── -->
              <div class="p-5 space-y-3">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Part 2 — Bank Details</p>
                <div v-if="!detail.scheme?.bank_name && !detail.scheme?.bank_account_number" class="text-sm text-gray-400 italic">Not provided.</div>
                <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  <div><span class="text-gray-400 text-xs block">Account Name</span>{{ detail.scheme?.bank_account_name || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Bank</span>{{ detail.scheme?.bank_name || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Account No.</span>{{ detail.scheme?.bank_account_number || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Branch</span>{{ detail.scheme?.bank_branch || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Bank Code</span>{{ detail.scheme?.bank_code || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">Branch Code</span>{{ detail.scheme?.branch_code || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">SWIFT Code</span>{{ detail.scheme?.swift_code || '—' }}</div>
                  <div><span class="text-gray-400 text-xs block">SORT/IBAN</span>{{ detail.scheme?.sort_or_iban_code || '—' }}</div>
                </div>
              </div>

              <!-- ── PART 3: AVC ── -->
              <div v-if="detail.scheme?.avc_amount || detail.scheme?.avc_percent" class="p-5 space-y-2">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Part 3 — Additional Voluntary Contributions</p>
                <div class="grid grid-cols-2 gap-3 text-sm">
                  <div v-if="detail.scheme?.avc_amount"><span class="text-gray-400 text-xs block">Amount (Kshs/month)</span>{{ detail.scheme.avc_amount }}</div>
                  <div v-if="detail.scheme?.avc_percent"><span class="text-gray-400 text-xs block">Percent (%/month)</span>{{ detail.scheme.avc_percent }}%</div>
                </div>
              </div>

              <!-- ── PART 4: BENEFICIARY NOMINATION ── -->
              <div class="p-5 space-y-3">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Part 4 — Beneficiary Nomination</p>
                <div v-if="!detail.nomination?.beneficiaries?.length" class="text-sm text-gray-400 italic">No beneficiaries recorded.</div>
                <div v-else class="rounded-lg border border-gray-200 overflow-hidden">
                  <table class="data-table text-sm w-full">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Relationship</th>
                        <th>Date of Birth</th>
                        <th>ID / Cert No.</th>
                        <th class="text-right">% Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(b, i) in detail.nomination.beneficiaries" :key="i">
                        <td class="font-medium">{{ b.full_name }}</td>
                        <td>{{ b.relationship }}</td>
                        <td>{{ b.date_of_birth || '—' }}</td>
                        <td>{{ b.id_number || b.birth_certificate_no || '—' }}</td>
                        <td class="text-right">{{ b.share_percent }}%</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="detail.nomination?.guardians?.length" class="space-y-1">
                  <p class="text-xs font-semibold text-gray-500 mt-2">Guardians</p>
                  <div v-for="(g, i) in detail.nomination.guardians" :key="i" class="text-sm text-gray-700">
                    <span class="font-medium">{{ g.guardian_name }}</span> — guardian of
                    <span class="font-medium">{{ g.beneficiary_name }}</span> · {{ g.relationship_to_beneficiary }}
                    <template v-if="g.id_number"> · ID {{ g.id_number }}</template>
                  </div>
                </div>
              </div>

              <!-- ── REVIEW ACTIONS ── -->
              <div class="p-5 space-y-4">
                <p class="text-xs font-bold text-navy uppercase tracking-wide">Review Actions</p>

                <!-- Scheme form review -->
                <div v-if="detail.scheme" class="space-y-2">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold text-gray-600">Occupational Scheme Form</span>
                    <StatusBadge :status="detail.scheme.status" />
                    <span class="text-xs text-gray-400">{{ detail.scheme.name }}</span>
                  </div>
                  <div v-if="detail.scheme.review_actions?.length" class="space-y-1">
                    <div v-for="(act, i) in detail.scheme.review_actions" :key="i" class="flex flex-wrap gap-2 text-xs items-center text-gray-600">
                      <StatusBadge :status="act.action" />
                      <span>by {{ act.reviewer }}</span>
                      <span v-if="act.action_on" class="text-gray-400">{{ formatDate(act.action_on) }}</span>
                      <span v-if="act.remarks" class="italic">— {{ act.remarks }}</span>
                    </div>
                  </div>
                  <ReviewPanel
                    v-if="detail.scheme.status === 'Submitted'"
                    form-type="scheme"
                    :name="detail.scheme.name"
                    @done="onReviewDone(row)"
                  />
                </div>
                <div v-else class="text-sm text-gray-400 italic">No Occupational Scheme Form on record.</div>

                <!-- Nomination review -->
                <div v-if="detail.nomination" class="space-y-2 pt-3 border-t border-gray-100">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold text-gray-600">Beneficiary Nomination</span>
                    <StatusBadge :status="detail.nomination.status" />
                    <span class="text-xs text-gray-400">{{ detail.nomination.name }}</span>
                  </div>
                  <div v-if="detail.nomination.review_actions?.length" class="space-y-1">
                    <div v-for="(act, i) in detail.nomination.review_actions" :key="i" class="flex flex-wrap gap-2 text-xs items-center text-gray-600">
                      <StatusBadge :status="act.action" />
                      <span>by {{ act.reviewer }}</span>
                      <span v-if="act.action_on" class="text-gray-400">{{ formatDate(act.action_on) }}</span>
                      <span v-if="act.remarks" class="italic">— {{ act.remarks }}</span>
                    </div>
                  </div>
                  <ReviewPanel
                    v-if="detail.nomination.status === 'Submitted'"
                    form-type="nomination"
                    :name="detail.nomination.name"
                    @done="onReviewDone(row)"
                  />
                </div>
                <div v-else class="text-sm text-gray-400 italic pt-3 border-t border-gray-100">No Beneficiary Nomination on record.</div>
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

const api = useApi()
const toast = useToast()

const statuses = ['Draft', 'Submitted', 'Needs More Info', 'Reviewed', 'Rejected', 'Superseded']

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

// Fetch the employee list — we use the scheme form list as the anchor, then
// fetch the nomination for each expanded employee separately.
async function load(p = 1) {
  page.value = p
  loading.value = true
  loadError.value = ''
  expanded.value = null
  detail.value = null

  try {
    const res = await api.call('onerc_compliance.api.v1.scheme.get_forms', {
      form_type: 'scheme',
      status: statusFilter.value || undefined,
      search: search.value || undefined,
      page: p,
      page_length: PAGE_LENGTH,
    })
    if (res.status !== 'success') { loadError.value = res.message || 'Failed to load.'; return }

    // Fetch nominations with no status filter so we always find them
    // regardless of their current status, keyed by employee doc name.
    const nomRes = await api.call('onerc_compliance.api.v1.scheme.get_forms', {
      form_type: 'nomination',
      search: search.value || undefined,
      page: 1,
      page_length: PAGE_LENGTH,
    })
    const nomMap = {}
    if (nomRes.status === 'success') {
      for (const r of nomRes.data) {
        if (r.employee) nomMap[r.employee] = r
      }
    }

    rows.value = res.data.map((r) => {
      const nom = nomMap[r.employee]
      return {
        employee: r.employee,
        employee_name: r.employee_name,
        employee_number: r.employee_number,
        department: r.department,
        scheme_name: r.name,
        scheme_status: r.status,
        nomination_name: nom?.name || null,
        nomination_status: nom?.status || null,
      }
    })
    totalCount.value = res.meta?.total_count ?? res.data.length
  } catch (e) {
    loadError.value = e.message || 'Failed to load.'
  } finally {
    loading.value = false
  }
}

async function toggleRow(row) {
  if (expanded.value === row.employee) {
    expanded.value = null
    detail.value = null
    return
  }
  expanded.value = row.employee
  detail.value = null
  detailLoading.value = true
  try {
    const [schemeRes, nomRes] = await Promise.all([
      row.scheme_name
        ? api.call('onerc_compliance.api.v1.scheme.get_form_detail', { form_type: 'scheme', name: row.scheme_name })
        : Promise.resolve({ status: 'success', data: null }),
      row.nomination_name
        ? api.call('onerc_compliance.api.v1.scheme.get_form_detail', { form_type: 'nomination', name: row.nomination_name })
        : Promise.resolve({ status: 'success', data: null }),
    ])
    detail.value = {
      scheme: schemeRes.status === 'success' ? schemeRes.data : null,
      nomination: nomRes.status === 'success' ? nomRes.data : null,
    }
  } catch (e) {
    toast.error(e.message || 'Failed to load detail.')
  } finally {
    detailLoading.value = false
  }
}

async function onReviewDone(row) {
  await toggleRow(row)   // collapse
  await load(page.value) // refresh list
  await toggleRow(row)   // re-expand with fresh data
}

function formatDate(val) {
  if (!val) return '—'
  return new Date(val).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

// Inline review panel component
const ReviewPanel = defineComponent({
  props: { formType: String, name: String },
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
          form_type: props.formType,
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
