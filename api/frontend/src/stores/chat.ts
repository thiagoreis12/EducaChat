import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, ErroApi, type Habilidade } from '../services/api'

export interface Mensagem {
  id: number
  papel: 'aluno' | 'assistente'
  texto: string
  habilidades?: Habilidade[]
  tempoMs?: number
  erro?: boolean
}

function mensagemDeErro(e: unknown): string {
  if (e instanceof ErroApi) {
    if (e.status === 503) return 'O assistente está ocupado agora. Tente de novo em instantes.'
    if (e.status === 409) return 'Seu perfil está incompleto: escolha sua série.'
    if (e.status === 401) return 'Sua sessão expirou. Entre novamente.'
    if (e.status === 0) return e.detalhe
  }
  return 'Não foi possível obter a resposta. Tente de novo.'
}

export const useChatStore = defineStore('chat', () => {
  const mensagens = ref<Mensagem[]>([])
  const carregando = ref(false)
  let proximoId = 1

  async function enviar(pergunta: string): Promise<void> {
    const texto = pergunta.trim()
    if (!texto || carregando.value) return
    mensagens.value.push({ id: proximoId++, papel: 'aluno', texto })
    carregando.value = true
    try {
      const r = await api.chat(texto)
      mensagens.value.push({
        id: proximoId++,
        papel: 'assistente',
        texto: r.resposta,
        habilidades: r.habilidades,
        tempoMs: r.tempo_ms,
      })
    } catch (e) {
      mensagens.value.push({ id: proximoId++, papel: 'assistente', texto: mensagemDeErro(e), erro: true })
    } finally {
      carregando.value = false
    }
  }

  function limpar(): void {
    mensagens.value = []
  }

  return { mensagens, carregando, enviar, limpar }
})
