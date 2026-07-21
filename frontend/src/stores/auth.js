import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(window.__frappe_user__ || 'Guest')
  const roles = ref(window.__frappe_roles__ || [])

  const isLoggedIn = computed(() => user.value && user.value !== 'Guest')
  const isOfficer = computed(() =>
    roles.value.includes('Compliance Officer') || roles.value.includes('System Manager')
  )
  const isHRManager = computed(() =>
    roles.value.includes('HR Manager') || roles.value.includes('System Manager')
  )

  async function checkSession() {
    try {
      const res = await fetch('/api/method/frappe.auth.get_logged_user')
      const json = await res.json()
      user.value = json.message || 'Guest'
      if (json.csrf_token) window.__csrf_token__ = json.csrf_token
    } catch {
      user.value = 'Guest'
    }
  }

  function redirectToLogin() {
    window.location.href = `/login?redirect-to=${encodeURIComponent(window.location.pathname)}`
  }

  return { user, roles, isLoggedIn, isOfficer, isHRManager, checkSession, redirectToLogin }
})
