import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import AppShell from '../components/layout/AppShell.vue'

const routes = [
  {
    path: '/compliance',
    component: AppShell,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'MyCompliance',
        component: () => import('../pages/MyCompliance.vue'),
      },
      {
        path: 'dashboard',
        name: 'ComplianceDashboard',
        component: () => import('../pages/ComplianceDashboard.vue'),
        meta: { requiresOfficer: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/compliance' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.matched.some((r) => r.meta.requiresAuth) && !auth.isLoggedIn) {
    auth.redirectToLogin()
    return false
  }

  if (to.meta.requiresOfficer && !auth.isOfficer) {
    return { name: 'MyCompliance' }
  }
})

export default router
