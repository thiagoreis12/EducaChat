import { createRouter, createWebHistory, type Router, type RouterHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requerAuth?: boolean
    soVisitante?: boolean
  }
}

export function criarRouter(history: RouterHistory = createWebHistory()): Router {
  const router = createRouter({
    history,
    routes: [
      { path: '/', redirect: '/chat' },
      { path: '/login', component: () => import('../views/Login.vue'), meta: { soVisitante: true } },
      {
        path: '/cadastro',
        component: () => import('../views/Cadastro.vue'),
        meta: { soVisitante: true },
      },
      { path: '/chat', component: () => import('../views/Chat.vue'), meta: { requerAuth: true } },
      { path: '/:qualquer(.*)*', redirect: '/chat' },
    ],
  })

  router.beforeEach(async (para) => {
    const auth = useAuthStore()
    // Na primeira navegação, tenta recuperar a sessão pelo cookie de refresh.
    await auth.inicializar()
    if (para.meta.requerAuth && !auth.autenticado) {
      return { path: '/login', query: { redirect: para.fullPath } }
    }
    if (para.meta.soVisitante && auth.autenticado) {
      return { path: '/chat' }
    }
    return true
  })

  return router
}
