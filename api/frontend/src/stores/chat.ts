import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, ErroApi, type Habilidade, type TurnoHistorico } from '../services/api'

export interface Mensagem {
  id: number
  papel: 'aluno' | 'assistente'
  texto: string
  habilidades?: Habilidade[]
  tempoMs?: number
  erro?: boolean
}

/** Quantas mensagens anteriores vão junto com cada pergunta (limite da API: 6). */
export const HISTORICO_MAX = 6

/**
 * Últimas trocas completas aluno → assistente, para o assistente lembrar da conversa.
 * Trocas que terminaram em erro ficam de fora (a pergunta sem resposta não ajuda o modelo).
 */
export function montarHistorico(mensagens: Mensagem[]): TurnoHistorico[] {
  const turnos: TurnoHistorico[] = []
  for (let i = 0; i + 1 < mensagens.length; i++) {
    const [pergunta, resposta] = [mensagens[i], mensagens[i + 1]]
    if (pergunta.papel === 'aluno' && resposta.papel === 'assistente' && !resposta.erro) {
      turnos.push({ papel: 'aluno', texto: pergunta.texto }, { papel: 'assistente', texto: resposta.texto })
      i++
    }
  }
  return turnos.slice(-HISTORICO_MAX)
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
    const historico = montarHistorico(mensagens.value)
    mensagens.value.push({ id: proximoId++, papel: 'aluno', texto })
    carregando.value = true
    try {
      const r = await api.chat(texto, historico)
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
