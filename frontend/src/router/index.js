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
      {
        path: 'scheme',
        name: 'SchemeForms',
        component: () => import('../pages/SchemeForms.vue'),
      },
      {
        path: 'pension-review',
        name: 'PensionReview',
        component: () => import('../pages/PensionReview.vue'),
        meta: { requiresHRManager: true },
      },
    ],
  },
  {
    path: '/ict-help',
    component: () => import('../pages/ict/IctPortal.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'IctHome', component: () => import('../pages/ict/HelpHome.vue') },
      { path: 'resources', name: 'IctResources', component: () => import('../pages/ict/ResourceAccess.vue') },
      { path: 'support', name: 'IctSupport', component: () => import('../pages/ict/SupportCenter.vue') },
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

  if (to.meta.requiresHRManager && !auth.isHRManager) {
    return { name: 'MyCompliance' }
  }
})

export default router
