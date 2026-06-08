<template>
  <router-view />

  <!-- Global toast container -->
  <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
    <transition-group name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-lg shadow-xl text-sm font-medium max-w-sm"
        :class="{
          'bg-success text-white': t.type === 'success',
          'bg-error text-white': t.type === 'error',
          'bg-navy text-white': t.type === 'info',
        }"
      >
        <span class="mt-0.5 flex-shrink-0">
          <svg v-if="t.type === 'success'" class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <svg v-else-if="t.type === 'error'" class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
          <svg v-else class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
          </svg>
        </span>
        <span class="flex-1">{{ t.message }}</span>
        <button class="ml-auto opacity-70 hover:opacity-100 flex-shrink-0" @click="dismiss(t.id)">×</button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { useToast } from './composables/useToast.js'
const { toasts, dismiss } = useToast()
</script>
