<template>
  <div class="p-6 max-w-3xl mx-auto">
    <div class="mb-6">
      <h2 class="text-xl font-bold text-navy">My Compliance Requirements</h2>
      <p class="text-sm text-gray-500 mt-0.5">Review and complete your assigned compliance tasks.</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-16 text-gray-400">
      <svg class="animate-spin w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      Loading requirements…
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="card p-4 border-l-4 border-error text-error text-sm">
      {{ loadError }}
    </div>

    <!-- Empty -->
    <div v-else-if="!requirements.length" class="card p-10 text-center text-gray-400">
      <svg class="w-10 h-10 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
      </svg>
      <p class="font-medium">No active compliance requirements</p>
      <p class="text-xs mt-1">Check back later or contact your Compliance Officer.</p>
    </div>

    <!-- Requirements list -->
    <div v-else class="space-y-4">
      <div v-for="req in requirements" :key="req.requirement" class="card overflow-hidden">
        <!-- Card header -->
        <div
          class="flex items-start justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
          @click="toggle(req)"
        >
          <div class="flex-1 min-w-0 mr-3">
            <div class="flex items-center gap-2 flex-wrap">
              <h3 class="font-semibold text-gray-900 text-sm">{{ req.title }}</h3>
              <StatusBadge :status="req.submission_status" />
            </div>
            <p v-if="req.deadline" class="text-xs text-gray-500 mt-1">
              Due {{ formatDate(req.deadline) }}
            </p>
          </div>
          <svg
            class="w-4 h-4 text-gray-400 flex-shrink-0 transition-transform mt-0.5"
            :class="expandedReq === req.requirement ? 'rotate-180' : ''"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </div>

        <!-- Expanded content -->
        <div v-if="expandedReq === req.requirement" class="border-t border-gray-100">
          <div class="p-4 space-y-4">
            <!-- Description -->
            <div
              v-if="req.description"
              class="text-sm text-gray-700 prose prose-sm max-w-none"
              v-html="req.description"
            />

            <!-- External link -->
            <a
              v-if="req.external_link"
              :href="req.external_link"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 text-sm text-primary hover:underline font-medium"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
              Reference Link
            </a>

            <!-- Reviewer remark (Needs More Info) -->
            <div
              v-if="req.submission_status === 'Needs More Info'"
              class="rounded-lg bg-orange-50 border border-orange-200 p-3 text-sm"
            >
              <p class="font-semibold text-orange-800 mb-1">Reviewer Note</p>
              <p class="text-orange-700">{{ latestRemark(req) || 'No remark provided.' }}</p>
            </div>

            <!-- Read-only state for non-editable statuses -->
            <template v-if="!isEditable(req)">
              <p class="text-xs text-gray-500 font-medium uppercase tracking-wide">Your Answers</p>
              <div v-if="req.field_schema.length" class="space-y-3">
                <div v-for="field in req.field_schema" :key="field.fieldname">
                  <p class="label">{{ field.label }}</p>
                  <div class="text-sm text-gray-800">{{ readableAnswer(req, field) }}</div>
                </div>
              </div>
              <p v-else class="text-sm text-gray-400 italic">No form fields for this requirement.</p>
            </template>

            <!-- Editable form -->
            <template v-else>
              <div v-if="req.field_schema.length" class="space-y-4">
                <div v-for="field in req.field_schema" :key="field.fieldname">
                  <label class="label">
                    {{ field.label }}
                    <span v-if="field.mandatory" class="required-asterisk">*</span>
                  </label>

                  <!-- Data (text) -->
                  <input
                    v-if="field.fieldtype === 'Data'"
                    type="text"
                    class="input-field"
                    v-model="formValues[req.requirement][field.fieldname]"
                  />

                  <!-- Small Text (textarea) -->
                  <textarea
                    v-else-if="field.fieldtype === 'Small Text'"
                    class="input-field resize-y"
                    rows="3"
                    v-model="formValues[req.requirement][field.fieldname]"
                  />

                  <!-- Check (checkbox) -->
                  <label
                    v-else-if="field.fieldtype === 'Check'"
                    class="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      class="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                      v-model="formValues[req.requirement][field.fieldname]"
                    />
                    <span class="text-sm text-gray-700">Yes</span>
                  </label>

                  <!-- Date -->
                  <input
                    v-else-if="field.fieldtype === 'Date'"
                    type="date"
                    class="input-field"
                    v-model="formValues[req.requirement][field.fieldname]"
                  />

                  <!-- Select -->
                  <select
                    v-else-if="field.fieldtype === 'Select'"
                    class="input-field appearance-none bg-white cursor-pointer"
                    v-model="formValues[req.requirement][field.fieldname]"
                  >
                    <option value="">Select an option…</option>
                    <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
                  </select>

                  <!-- Int / Float -->
                  <input
                    v-else-if="field.fieldtype === 'Int' || field.fieldtype === 'Float'"
                    type="number"
                    class="input-field"
                    :step="field.fieldtype === 'Float' ? 'any' : '1'"
                    v-model="formValues[req.requirement][field.fieldname]"
                  />

                  <!-- Attach -->
                  <div v-else-if="field.fieldtype === 'Attach'" class="space-y-2">
                    <div v-if="formValues[req.requirement][field.fieldname]" class="flex items-center gap-2 text-xs">
                      <a
                        :href="formValues[req.requirement][field.fieldname]"
                        target="_blank"
                        class="text-primary hover:underline"
                      >View current file</a>
                      <button
                        class="text-gray-400 hover:text-gray-600"
                        @click="formValues[req.requirement][field.fieldname] = ''"
                      >Remove</button>
                    </div>
                    <div
                      v-if="uploadingField[req.requirement]?.[field.fieldname]"
                      class="text-xs text-gray-500"
                    >Uploading…</div>
                    <input
                      v-else
                      type="file"
                      class="text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0
                             file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700
                             hover:file:bg-gray-200 cursor-pointer"
                      @change="(e) => handleFileUpload(e, req.requirement, field.fieldname)"
                    />
                  </div>
                </div>
              </div>

              <!-- Submit button -->
              <div class="pt-2 flex items-center gap-3">
                <button
                  class="btn-primary"
                  :disabled="!canSubmit(req) || submitting"
                  @click="submitRequirement(req)"
                >
                  <span v-if="submitting && submittingReq === req.requirement">Submitting…</span>
                  <span v-else>Submit</span>
                </button>
                <p v-if="!canSubmit(req)" class="text-xs text-gray-400">
                  Fill in all required fields to submit.
                </p>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useApi } from '../composables/useApi.js'
import { useToast } from '../composables/useToast.js'
import StatusBadge from '../components/StatusBadge.vue'

const { call, upload } = useApi()
const toast = useToast()

const loading = ref(false)
const loadError = ref('')
const requirements = ref([])
const expandedReq = ref(null)
const formValues = reactive({})
const uploadingField = reactive({})
const submitting = ref(false)
const submittingReq = ref(null)

onMounted(loadRequirements)

async function loadRequirements() {
  loading.value = true
  loadError.value = ''
  try {
    const result = await call('onerc_compliance.api.v1.compliance.get_my_requirements')
    if (result?.status === 'error') {
      loadError.value = result.message || 'Failed to load requirements.'
      requirements.value = []
      return
    }
    requirements.value = Array.isArray(result?.data) ? result.data : []
    for (const req of requirements.value) {
      initFormValues(req)
    }
  } catch (e) {
    loadError.value = e.message || 'Failed to load requirements.'
  } finally {
    loading.value = false
  }
}

function initFormValues(req) {
  if (!formValues[req.requirement]) {
    formValues[req.requirement] = {}
  }
  for (const field of req.field_schema) {
    const ans = req.answers?.[field.fieldname]
    let val
    if (!ans) {
      val = field.fieldtype === 'Check' ? false : ''
    } else if (field.fieldtype === 'Check') {
      val = ans.value_check || false
    } else if (field.fieldtype === 'Date') {
      val = ans.value_date || ''
    } else if (field.fieldtype === 'Attach') {
      val = ans.attachment || ''
    } else {
      val = ans.value || ''
    }
    formValues[req.requirement][field.fieldname] = val
  }
}

function toggle(req) {
  expandedReq.value = expandedReq.value === req.requirement ? null : req.requirement
}

function isEditable(req) {
  return req.submission_status === 'Pending' || req.submission_status === 'Needs More Info'
}

function latestRemark(req) {
  const actions = req.review_actions || []
  for (let i = actions.length - 1; i >= 0; i--) {
    if (actions[i].remarks) return actions[i].remarks
  }
  return ''
}

function canSubmit(req) {
  const vals = formValues[req.requirement] || {}
  return req.field_schema.every((f) => {
    if (!f.mandatory) return true
    const v = vals[f.fieldname]
    if (f.fieldtype === 'Check') return !!v
    return v !== undefined && v !== null && String(v).trim() !== ''
  })
}

function readableAnswer(req, field) {
  const ans = req.answers?.[field.fieldname]
  if (!ans) return '—'
  if (field.fieldtype === 'Check') return ans.value_check ? 'Yes' : 'No'
  if (field.fieldtype === 'Date') return ans.value_date || '—'
  if (field.fieldtype === 'Attach') return ans.attachment ? '(file uploaded)' : '—'
  return ans.value || '—'
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

async function handleFileUpload(event, reqName, fieldname) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!uploadingField[reqName]) uploadingField[reqName] = {}
  uploadingField[reqName][fieldname] = true
  try {
    const url = await upload(file)
    formValues[reqName][fieldname] = url
  } catch (e) {
    toast.error(e.message || 'File upload failed.')
  } finally {
    uploadingField[reqName][fieldname] = false
  }
}

async function submitRequirement(req) {
  submitting.value = true
  submittingReq.value = req.requirement
  const vals = formValues[req.requirement] || {}
  const answers = {}
  for (const field of req.field_schema) {
    const v = vals[field.fieldname]
    if (field.fieldtype === 'Check') {
      answers[field.fieldname] = !!v
    } else if (field.fieldtype === 'Date') {
      answers[field.fieldname] = v || null
    } else if (field.fieldtype === 'Attach') {
      answers[field.fieldname] = v || null
    } else if (field.fieldtype === 'Int') {
      answers[field.fieldname] = v !== '' && v !== null ? parseInt(v, 10) : null
    } else if (field.fieldtype === 'Float') {
      answers[field.fieldname] = v !== '' && v !== null ? parseFloat(v) : null
    } else {
      answers[field.fieldname] = v || ''
    }
  }

  try {
    const result = await call('onerc_compliance.api.v1.compliance.submit_requirement', {
      requirement: req.requirement,
      answers: JSON.stringify(answers),
    })
    const newStatus = result?.data?.status || 'Submitted'
    toast.success(`Submitted successfully. Status: ${newStatus}`)
    expandedReq.value = null
    await loadRequirements()
  } catch (e) {
    toast.error(e.message || 'Submission failed. Please try again.')
  } finally {
    submitting.value = false
    submittingReq.value = null
  }
}
</script>
