<template>
  <span
    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap"
    :class="classes"
  >{{ status }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ status: { type: String, default: '' } })

const classes = computed(() => {
  switch (props.status) {
    case 'Pending':        return 'bg-amber-100 text-amber-800'
    case 'Submitted':      return 'bg-blue-100 text-blue-800'
    case 'Needs More Info': return 'bg-orange-100 text-orange-800'
    case 'Reviewed':       return 'bg-green-100 text-green-800'
    case 'Rejected':       return 'bg-red-100 text-red-800'
    case 'Overdue':        return 'bg-rose-100 text-rose-800'
    case 'Exempted':       return 'bg-gray-100 text-gray-600'
    case 'Draft':          return 'bg-slate-100 text-slate-600'
    case 'Superseded':     return 'bg-purple-100 text-purple-700'
    default:               return 'bg-gray-100 text-gray-500'
  }
})
</script>
