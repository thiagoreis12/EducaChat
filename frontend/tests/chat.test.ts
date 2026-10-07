import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../src/stores/auth'
import { HISTORICO_MAX, montarHistorico, useChatStore, type Mensagem } from '../src/stores/chat'
import { mockFetch, sessao } from './utils'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.unstubAllGlobals()
})

const resposta = (texto: string) => ({
  status: 200,
  corpo: { resposta: texto, serie: '6º ano', habilidades: [], tempo_ms: 1 },
})

describe('histórico da conversa', () => {
  it('envia as trocas anteriores junto com a nova pergunta, sem a série', async () => {
    let n = 0
    const chamadas = mockFetch({
      'POST /auth/login': () => ({ status: 200, corpo: sessao('tok-1') }),
      'POST /chat': () => resposta(`r${++n}`),
    })
    await useAuthStore().entrar('a@escola.br', 'senha')
    const chat = useChatStore()
    await chat.enviar('o que é fração?')
    await chat.enviar('e como somo duas?')

    const [primeira, segunda] = chamadas.filter((c) => c.url === '/chat')
    expect(primeira.corpo).toEqual({ pergunta: 'o que é fração?' })
    expect(segunda.corpo).toEqual({
      pergunta: 'e como somo duas?',
      historico: [
        { papel: 'aluno', texto: 'o que é fração?' },
        { papel: 'assistente', texto: 'r1' },
      ],
    })
  })

  it('deixa de fora trocas que terminaram em erro', () => {
    const msgs: Mensagem[] = [
      { id: 1, papel: 'aluno', texto: 'p1' },
      { id: 2, papel: 'assistente', texto: 'falhou', erro: true },
      { id: 3, papel: 'aluno', texto: 'p2' },
      { id: 4, papel: 'assistente', texto: 'r2' },
    ]
    expect(montarHistorico(msgs)).toEqual([
      { papel: 'aluno', texto: 'p2' },
      { papel: 'assistente', texto: 'r2' },
    ])
  })

  it('manda só as últimas mensagens', () => {
    const msgs: Mensagem[] = []
    for (let i = 0; i < 10; i++) {
      msgs.push({ id: 2 * i, papel: 'aluno', texto: `p${i}` }, { id: 2 * i + 1, papel: 'assistente', texto: `r${i}` })
    }
    const h = montarHistorico(msgs)
    expect(h).toHaveLength(HISTORICO_MAX)
    expect(h[0]).toEqual({ papel: 'aluno', texto: 'p7' })
    expect(h.at(-1)).toEqual({ papel: 'assistente', texto: 'r9' })
  })
})
