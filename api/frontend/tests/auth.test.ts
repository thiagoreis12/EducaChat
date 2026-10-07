import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../src/services/api'
import { destinoSeguro } from '../src/services/redirect'
import { useAuthStore } from '../src/stores/auth'
import { mockFetch, sessao } from './utils'

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  sessionStorage.clear()
  vi.unstubAllGlobals()
})

describe('sessão', () => {
  it('login guarda o token só em memória, nunca em storage', async () => {
    const chamadas = mockFetch({ 'POST /auth/login': () => ({ status: 200, corpo: sessao('tok-1') }) })
    const auth = useAuthStore()
    await auth.entrar('a@escola.br', 'senha')
    expect(auth.token).toBe('tok-1')
    expect(auth.perfil).toEqual({ ano: 6, serie: '6º ano' })
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
    expect(document.cookie).toBe('')
    expect(chamadas[0].credentials).toBe('include') // permite o cookie HttpOnly de refresh
  })

  it('chat não envia a série: só a pergunta, com o token', async () => {
    const chamadas = mockFetch({
      'POST /auth/login': () => ({ status: 200, corpo: sessao('tok-1', 6) }),
      'POST /chat': () => ({ status: 200, corpo: { resposta: 'ok', serie: '6º ano', habilidades: [], tempo_ms: 1 } }),
    })
    await useAuthStore().entrar('a@escola.br', 'senha')
    await api.chat('o que é fração?')
    const chat = chamadas.find((c) => c.url === '/chat')!
    expect(chat.corpo).toEqual({ pergunta: 'o que é fração?' })
    expect(chat.auth).toBe('Bearer tok-1')
  })

  it('em 401 renova uma vez pelo cookie e repete a chamada', async () => {
    let tentativas = 0
    const chamadas = mockFetch({
      'POST /auth/login': () => ({ status: 200, corpo: sessao('velho') }),
      'POST /auth/refresh': () => ({ status: 200, corpo: sessao('novo') }),
      'POST /chat': (c) => {
        tentativas++
        return c.auth === 'Bearer novo'
          ? { status: 200, corpo: { resposta: 'ok', serie: '6º ano', habilidades: [], tempo_ms: 1 } }
          : { status: 401, corpo: { detail: 'token inválido ou expirado' } }
      },
    })
    const auth = useAuthStore()
    await auth.entrar('a@escola.br', 'senha')
    await expect(api.chat('x')).resolves.toMatchObject({ resposta: 'ok' })
    expect(tentativas).toBe(2)
    expect(auth.token).toBe('novo')
    expect(chamadas.filter((c) => c.url === '/auth/refresh')).toHaveLength(1)
  })

  it('renovações concorrentes compartilham uma única chamada de refresh', async () => {
    const chamadas = mockFetch({
      'POST /auth/login': () => ({ status: 200, corpo: sessao('velho') }),
      'POST /auth/refresh': () => ({ status: 200, corpo: sessao('novo') }),
      'POST /chat': (c) =>
        c.auth === 'Bearer novo'
          ? { status: 200, corpo: { resposta: 'ok', serie: '6º ano', habilidades: [], tempo_ms: 1 } }
          : { status: 401 },
    })
    await useAuthStore().entrar('a@escola.br', 'senha')
    await Promise.all([api.chat('a'), api.chat('b'), api.chat('c')])
    expect(chamadas.filter((c) => c.url === '/auth/refresh')).toHaveLength(1)
  })

  it('refresh falhou: sessão é limpa e marcada como expirada', async () => {
    mockFetch({
      'POST /auth/login': () => ({ status: 200, corpo: sessao('velho') }),
      'POST /auth/refresh': () => ({ status: 401, corpo: { detail: 'sessão expirada' } }),
      'POST /chat': () => ({ status: 401 }),
    })
    const auth = useAuthStore()
    await auth.entrar('a@escola.br', 'senha')
    await expect(api.chat('x')).rejects.toMatchObject({ status: 401 })
    expect(auth.autenticado).toBe(false)
    expect(auth.sessaoExpirada).toBe(true)
  })

  it('inicializar recupera a sessão pelo cookie (recarregar a página)', async () => {
    mockFetch({ 'POST /auth/refresh': () => ({ status: 200, corpo: sessao('restaurado', 8) }) })
    const auth = useAuthStore()
    await auth.inicializar()
    expect(auth.token).toBe('restaurado')
    expect(auth.perfil?.serie).toBe('8º ano')
  })

  it('cadastro com confirmação de e-mail pendente', async () => {
    const chamadas = mockFetch({
      'POST /auth/cadastro': () => ({ status: 201, corpo: { confirmacao_pendente: true, sessao: null } }),
    })
    const auth = useAuthStore()
    await expect(auth.cadastrar('a@escola.br', '123456', 7)).resolves.toBe('confirmar_email')
    expect(chamadas[0].corpo).toEqual({ email: 'a@escola.br', senha: '123456', ano: 7 })
    expect(auth.autenticado).toBe(false)
  })
})

describe('destinoSeguro', () => {
  it.each([
    ['/chat', '/chat'],
    ['/chat?x=1', '/chat?x=1'],
    ['https://malicioso.com', '/chat'],
    ['//malicioso.com', '/chat'],
    ['/\\malicioso.com', '/chat'],
    [undefined, '/chat'],
    [['/a', '/b'], '/chat'],
  ])('%s -> %s', (entrada, esperado) => {
    expect(destinoSeguro(entrada)).toBe(esperado)
  })
})
