import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import { criarRouter } from '../src/router'
import { useAuthStore } from '../src/stores/auth'
import { mockFetch, sessao } from './utils'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.unstubAllGlobals()
})

describe('guarda de rota', () => {
  it('sem sessão, /chat redireciona para /login preservando o destino', async () => {
    mockFetch({ 'POST /auth/refresh': () => ({ status: 401 }) })
    const router = criarRouter(createMemoryHistory())
    await router.push('/chat')
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/chat')
  })

  it('com sessão recuperada pelo cookie, /chat abre direto', async () => {
    mockFetch({ 'POST /auth/refresh': () => ({ status: 200, corpo: sessao('t') }) })
    const router = criarRouter(createMemoryHistory())
    await router.push('/chat')
    expect(router.currentRoute.value.path).toBe('/chat')
  })

  it('autenticado não volta para login/cadastro', async () => {
    mockFetch({ 'POST /auth/refresh': () => ({ status: 200, corpo: sessao('t') }) })
    const router = criarRouter(createMemoryHistory())
    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/chat')
    await router.push('/cadastro')
    expect(router.currentRoute.value.path).toBe('/chat')
  })

  it('o refresh inicial acontece uma única vez entre navegações', async () => {
    const chamadas = mockFetch({ 'POST /auth/refresh': () => ({ status: 401 }) })
    const router = criarRouter(createMemoryHistory())
    await router.push('/login')
    await router.push('/cadastro')
    await router.push('/chat')
    expect(chamadas.filter((c) => c.url === '/auth/refresh')).toHaveLength(1)
    expect(useAuthStore().inicializado).toBe(true)
  })
})
