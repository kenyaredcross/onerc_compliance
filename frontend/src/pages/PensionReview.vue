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
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold text-gray-600">Pension Compliance Form</span>
                    <StatusBadge :status="detail.status" />
                    <span class="text-xs text-gray-400">{{ detail.name }}</span>
                    <span v-if="detail.amends" class="text-xs text-gray-400">(amends {{ detail.amends }})</span>
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

function formatDate(val) {
  if (!val) return '-'
  return new Date(val).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
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
