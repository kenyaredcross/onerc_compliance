<template>
  <div class="p-6 space-y-6">
    <!-- Page header -->
    <div>
      <h2 class="text-xl font-bold text-navy">Compliance Dashboard</h2>
      <p class="text-sm text-gray-500 mt-0.5">Review submissions and track completion by requirement.</p>
    </div>

    <!-- Requirement selector -->
    <div class="card p-4">
      <label class="label">Select Requirement</label>
      <div class="flex gap-3 items-center">
        <select
          class="input-field max-w-md"
          v-model="selectedRequirement"
          @change="onRequirementChange"
        >
          <option value="">— choose a requirement —</option>
          <option v-for="r in requirementList" :key="r.name" :value="r.name">
            {{ r.title }}
          </option>
        </select>
        <button
          v-if="selectedRequirement"
          class="btn-secondary text-sm"
          @click="refresh"
          :disabled="dashLoading"
        >Refresh</button>
      </div>
      <p v-if="reqListError" class="text-xs text-error mt-2">{{ reqListError }}</p>
    </div>

    <!-- Stats (get_dashboard) -->
    <template v-if="selectedRequirement">
      <div v-if="dashLoading" class="flex items-center gap-2 text-gray-400 text-sm py-4">
        <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
        Loading…
      </div>

      <template v-else-if="dashboard">
        <!-- Completion bar -->
        <div class="card p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">Overall Completion</span>
            <span class="text-sm font-bold text-navy">{{ dashboard.completion_percent }}%</span>
          </div>
          <div class="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full bg-success transition-all"
              :style="{ width: dashboard.completion_percent + '%' }"
            />
          </div>
          <p class="text-xs text-gray-400 mt-1.5">
            {{ dashboard.reviewed_count }} reviewed out of {{ dashboard.expected_headcount || dashboard.known_total }} expected
          </p>
        </div>

        <!-- Status count cards -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <div
            v-for="label in statusOrder"
            :key="label"
            class="card p-4 text-center"
          >
            <p class="text-2xl font-bold" :class="statusColor(label)">
              {{ dashboard.status_counts[label] || 0 }}
            </p>
            <p class="text-xs text-gray-500 mt-1 font-medium">{{ label }}</p>
          </div>
        </div>

        <!-- Department breakdown -->
        <div v-if="dashboard.by_department?.length" class="card overflow-hidden">
          <div class="px-4 py-3 border-b border-gray-100">
            <h3 class="text-sm font-semibold text-gray-700">By Department</h3>
          </div>
          <div class="table-wrap shadow-none rounded-none border-0">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Reviewed</th>
                  <th>Total</th>
                  <th>Progress</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in dashboard.by_department" :key="row.department">
                  <td>{{ row.department }}</td>
                  <td>{{ row.reviewed }}</td>
                  <td>{{ row.total }}</td>
                  <td>
                    <div class="flex items-center gap-2">
                      <div class="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          class="h-full bg-success rounded-full"
                          :style="{ width: pct(row.reviewed, row.total) + '%' }"
                        />
                      </div>
                      <span class="text-xs text-gray-500">{{ pct(row.reviewed, row.total) }}%</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- Submission list (get_submissions) -->
      <div class="card overflow-hidden">
        <!-- Filter bar -->
        <div class="px-4 py-3 border-b border-gray-100 space-y-3">
          <div class="flex items-center gap-3 flex-wrap">
            <h3 class="text-sm font-semibold text-gray-700 flex-1">Submissions</h3>
            <button
              v-if="hasActiveFilters"
              class="btn-secondary text-xs py-1.5"
              @click="clearFilters"
            >Clear filters</button>
          </div>
          <div class="flex items-center gap-3 flex-wrap">
            <!-- Search -->
            <div class="relative flex-1 min-w-[12rem]">
              <svg
                class="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z"/>
              </svg>
              <input
                type="text"
                class="input-field text-sm pl-9"
                placeholder="Search by name or staff ID"
                v-model="searchTerm"
                @input="onSearchInput"
              />
            </div>
            <!-- Department -->
            <select
              class="input-field text-sm w-44"
              v-model="departmentFilter"
              @change="onFilterChange"
            >
              <option value="">All departments</option>
              <option v-for="d in departmentOptions" :key="d" :value="d">{{ d }}</option>
            </select>
            <!-- Status -->
            <select
              class="input-field text-sm w-44"
              v-model="statusFilter"
              @change="onFilterChange"
            >
              <option value="">All statuses</option>
              <option v-for="s in statusOrder" :key="s" :value="s">{{ s }}</option>
              <option value="Exempted">Exempted</option>
            </select>
          </div>
        </div>

        <div v-if="subsLoading" class="py-8 text-center text-gray-400 text-sm">Loading submissions…</div>
        <div v-else-if="!submissions.length && hasActiveFilters" class="py-8 text-center text-gray-400 text-sm">
          No submissions match these filters.
        </div>
        <div v-else-if="!submissions.length" class="py-8 text-center text-gray-400 text-sm">
          No submissions found.
        </div>
        <div v-else class="divide-y divide-gray-50">
          <div v-for="sub in submissions" :key="sub.name">
            <!-- Row -->
            <div
              class="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
              @click="toggleSub(sub)"
            >
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">{{ sub.employee_name || sub.name }}</p>
                <p class="text-xs text-gray-500">{{ sub.department || 'No department' }}</p>
              </div>
              <StatusBadge :status="sub.status" />
              <p class="text-xs text-gray-400 hidden sm:block w-28 text-right">
                {{ sub.submitted_on ? formatDate(sub.submitted_on) : '—' }}
              </p>
              <svg
                class="w-4 h-4 text-gray-300 flex-shrink-0 transition-transform"
                :class="expandedSub === sub.name ? 'rotate-180' : ''"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>

            <!-- Expanded detail -->
            <div v-if="expandedSub === sub.name" class="bg-gray-50 border-t border-gray-100 p-4 space-y-4">
              <!-- Answers -->
              <div v-if="sub.field_schema?.length">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Answers</p>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div v-for="field in sub.field_schema" :key="field.fieldname">
                    <p class="text-xs text-gray-500 font-medium">{{ field.label }}</p>
                    <template v-if="sub.answers[field.fieldname]">
                      <a
                        v-if="field.fieldtype === 'Attach' && sub.answers[field.fieldname].attachment"
                        :href="sub.answers[field.fieldname].attachment"
                        target="_blank"
                        class="text-sm text-primary hover:underline"
                      >View attachment</a>
                      <span v-else-if="field.fieldtype === 'Check'" class="text-sm text-gray-800">
                        {{ sub.answers[field.fieldname].value_check ? 'Yes' : 'No' }}
                      </span>
                      <span v-else-if="field.fieldtype === 'Date'" class="text-sm text-gray-800">
                        {{ sub.answers[field.fieldname].value_date || '—' }}
                      </span>
                      <span v-else class="text-sm text-gray-800">
                        {{ sub.answers[field.fieldname].value || '—' }}
                      </span>
                    </template>
                    <span v-else class="text-sm text-gray-400">—</span>
                  </div>
                </div>
              </div>

              <!-- Review history -->
              <div v-if="sub.review_actions?.length">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Review History</p>
                <div class="space-y-2">
                  <div
                    v-for="(act, i) in sub.review_actions"
                    :key="i"
                    class="flex gap-3 text-sm"
                  >
                    <StatusBadge :status="act.action" />
                    <span class="text-gray-500">by {{ act.reviewer }}</span>
                    <span v-if="act.action_on" class="text-gray-400 text-xs self-center">{{ formatDate(act.action_on) }}</span>
                    <span v-if="act.remarks" class="text-gray-700 italic">— {{ act.remarks }}</span>
                  </div>
                </div>
              </div>

              <!-- Review panel for Submitted submissions -->
              <div v-if="sub.status === 'Submitted'" class="pt-2 border-t border-gray-200">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Take Action</p>

                <!-- Active review form for this submission -->
                <template v-if="activeReview?.name === sub.name">
                  <div class="space-y-3">
                    <div v-if="activeReview.action !== 'Reviewed'">
                      <label class="label">
                        Remarks
                        <span class="required-asterisk">*</span>
                      </label>
                      <textarea
                        v-model="activeReview.remarks"
                        class="input-field resize-none"
                        rows="3"
                        :placeholder="`Required for ${activeReview.action}`"
                      />
                    </div>
                    <div v-else class="text-sm text-gray-500">
                      Mark this submission as reviewed. Remarks are optional.
                    </div>
                    <div class="flex gap-2">
                      <button
                        class="btn-primary"
                        :disabled="!canReview || reviewing"
                        @click="submitReview"
                      >
                        <span v-if="reviewing">Processing…</span>
                        <span v-else>Confirm {{ activeReview.action }}</span>
                      </button>
                      <button class="btn-secondary" @click="activeReview = null">Cancel</button>
                    </div>
                  </div>
                </template>

                <!-- Action buttons -->
                <template v-else>
                  <div class="flex gap-2 flex-wrap">
                    <button class="btn-success" @click="startReview(sub, 'Reviewed')">
                      Mark Reviewed
                    </button>
                    <button class="btn-warning" @click="startReview(sub, 'Needs More Info')">
                      Needs More Info
                    </button>
                    <button class="btn-danger" @click="startReview(sub, 'Rejected')">
                      Reject
                    </button>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- Result count + pagination -->
        <div
          v-if="!subsLoading && submissions.length"
          class="px-4 py-3 border-t border-gray-100 flex items-center justify-between gap-3 flex-wrap"
        >
          <p class="text-xs text-gray-500">
            Showing {{ submissions.length }} of {{ totalCount }} submissions
          </p>
          <div v-if="totalPages > 1" class="flex items-center gap-2">
            <button
              class="btn-secondary text-xs py-1.5"
              :disabled="page <= 1"
              @click="goToPage(page - 1)"
            >Previous</button>
            <span class="text-xs text-gray-500">Page {{ page }} of {{ totalPages }}</span>
            <button
              class="btn-secondary text-xs py-1.5"
              :disabled="page >= totalPages"
              @click="goToPage(page + 1)"
            >Next</button>
          </div>
        </div>
      </div>
    </template>

    <!-- Prompt when no requirement selected -->
    <div v-if="!selectedRequirement" class="card p-10 text-center text-gray-400">
      <p class="text-sm">Select a requirement above to view submissions and statistics.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useApi } from '../composables/useApi.js'
import { useToast } from '../composables/useToast.js'
import StatusBadge from '../components/StatusBadge.vue'

const { call } = useApi()
const toast = useToast()

const requirementList = ref([])
const reqListError = ref('')
const selectedRequirement = ref('')
const statusFilter = ref('')
const searchTerm = ref('')
const departmentFilter = ref('')

const page = ref(1)
const pageLength = 50
const totalCount = ref(0)

const dashLoading = ref(false)
const subsLoading = ref(false)
const dashboard = ref(null)
const submissions = ref([])

const departmentOptions = computed(() => dashboard.value?.departments || [])
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageLength)))
const hasActiveFilters = computed(
  () => !!(searchTerm.value.trim() || departmentFilter.value || statusFilter.value)
)

const expandedSub = ref(null)
const activeReview = ref(null)
const reviewing = ref(false)

const statusOrder = ['Reviewed', 'Submitted', 'Pending', 'Needs More Info', 'Overdue']

onMounted(loadRequirementList)

async function loadRequirementList() {
  try {
    const result = await call('frappe.client.get_list', {
      doctype: 'Compliance Requirement',
      filters: JSON.stringify([['status', '=', 'Active']]),
      fields: JSON.stringify(['name', 'title']),
      limit: 200,
    })
    requirementList.value = Array.isArray(result) ? result : (result?.message || [])
  } catch (e) {
    reqListError.value = e.message || 'Could not load requirements.'
  }
}

async function onRequirementChange() {
  // Switching requirement: drop any filters and paging from the previous one.
  resetFilterState()
  if (!selectedRequirement.value) {
    dashboard.value = null
    submissions.value = []
    totalCount.value = 0
    return
  }
  await refresh()
}

function resetFilterState() {
  searchTerm.value = ''
  departmentFilter.value = ''
  statusFilter.value = ''
  page.value = 1
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
}

let searchTimer = null

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadSubmissions()
  }, 300)
}

// Status / department change: reset to the first page, then reload.
function onFilterChange() {
  page.value = 1
  loadSubmissions()
}

function clearFilters() {
  resetFilterState()
  loadSubmissions()
}

function goToPage(target) {
  if (target < 1 || target > totalPages.value) return
  page.value = target
  loadSubmissions()
}

async function refresh() {
  await Promise.all([loadDashboard(), loadSubmissions()])
}

async function loadDashboard() {
  dashLoading.value = true
  try {
    const result = await call('onerc_compliance.api.v1.compliance.get_dashboard', {
      requirement: selectedRequirement.value,
    })
    dashboard.value = result?.data || null
  } catch (e) {
    toast.error(e.message || 'Failed to load dashboard.')
  } finally {
    dashLoading.value = false
  }
}

async function loadSubmissions() {
  subsLoading.value = true
  try {
    const args = {
      requirement: selectedRequirement.value,
      page: page.value,
      page_length: pageLength,
    }
    if (statusFilter.value) args.status = statusFilter.value
    if (departmentFilter.value) args.department = departmentFilter.value
    if (searchTerm.value.trim()) args.search = searchTerm.value.trim()
    const result = await call('onerc_compliance.api.v1.compliance.get_submissions', args)
    submissions.value = result?.data || []
    totalCount.value = result?.meta?.total_count ?? submissions.value.length
  } catch (e) {
    toast.error(e.message || 'Failed to load submissions.')
  } finally {
    subsLoading.value = false
  }
}

function toggleSub(sub) {
  if (expandedSub.value === sub.name) {
    expandedSub.value = null
    activeReview.value = null
  } else {
    expandedSub.value = sub.name
    activeReview.value = null
  }
}

function startReview(sub, action) {
  activeReview.value = { name: sub.name, action, remarks: '' }
}

const canReview = computed(() => {
  if (!activeReview.value) return false
  if (activeReview.value.action === 'Reviewed') return true
  return (activeReview.value.remarks || '').trim().length > 0
})

async function submitReview() {
  if (!canReview.value) return
  reviewing.value = true
  try {
    await call('onerc_compliance.api.v1.compliance.review_submission', {
      submission: activeReview.value.name,
      action: activeReview.value.action,
      remarks: activeReview.value.remarks || '',
    })
    toast.success(`Submission marked as "${activeReview.value.action}".`)
    activeReview.value = null
    expandedSub.value = null
    await refresh()
  } catch (e) {
    toast.error(e.message || 'Review action failed.')
  } finally {
    reviewing.value = false
  }
}

function pct(reviewed, total) {
  if (!total) return 0
  return Math.round((reviewed / total) * 100)
}

function statusColor(status) {
  switch (status) {
    case 'Reviewed':       return 'text-success'
    case 'Submitted':      return 'text-blue-600'
    case 'Pending':        return 'text-amber-600'
    case 'Needs More Info': return 'text-orange-600'
    case 'Overdue':        return 'text-rose-600'
    default:               return 'text-gray-700'
  }
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>
