<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
    <div>
      <label class="label">Scheme Name</label>
      <input type="text" class="input-field bg-gray-50" :value="schemeName" disabled />
    </div>
    <div>
      <label class="label">Member's Full Name <span class="required-asterisk">*</span></label>
      <input type="text" class="input-field" v-model="modelValue.member_full_name" :disabled="!editable" />
    </div>
    <div>
      <label class="label">Email</label>
      <input type="email" class="input-field" v-model="modelValue.email" :disabled="!editable" />
    </div>
    <div>
      <label class="label">Mobile / Tel No.</label>
      <input type="text" class="input-field" :value="mobile" @input="onMobileInput" :disabled="!editable" />
    </div>
    <div>
      <label class="label">ID No. <span class="required-asterisk">*</span></label>
      <input type="text" class="input-field" v-model="modelValue.id_number" :disabled="!editable" />
    </div>
    <div>
      <label class="label">KRA PIN No.</label>
      <input type="text" class="input-field" v-model="modelValue.kra_pin" :disabled="!editable" />
    </div>
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
  schemeName: { type: String, default: '' },
  editable: { type: Boolean, default: true },
})

// The scheme form stores mobile as `mobile_number`; the nomination form stores
// it as `telephone`. We read whichever key is present and write back to both
// so the parent reactive object stays correct regardless of form type.
const mobile = computed(() =>
  props.modelValue.mobile_number ?? props.modelValue.telephone ?? ''
)

function onMobileInput(e) {
  const val = e.target.value
  if ('mobile_number' in props.modelValue) props.modelValue.mobile_number = val
  if ('telephone' in props.modelValue) props.modelValue.telephone = val
}
</script>
