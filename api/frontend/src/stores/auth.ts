import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, configurarSessao, ErroApi, type Perfil, type Sessao } from '../services/api'

/**
 * Sessão do aluno.
 *
 * Decisão de segurança (docs/decisoes.md, D25): o access token fica SÓ em memória (este
 * store não é persistido), e o refresh token fica num cookie HttpOnly que o JavaScript
 * não lê. Ao recarregar a página, `inicializar()` recupera a sessão via /auth/refresh.
 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const usuarioId = ref<string | null>(null)
  const email = ref<string | null>(null)
  const perfil = ref<Perfil | null>(null)
  const inicializado = ref(false)
  const sessaoExpirada = ref(false)

  const autenticado = computed(() => token.value !== null)

  function aplicar(s: Sessao): void {
    token.value = s.access_token
    usuarioId.value = s.usuario_id
    email.value = s.email
    perfil.value = s.perfil
    sessaoExpirada.value = false
  }

  function limpar(): void {
    token.value = null
    usuarioId.value = null
    email.value = null
    perfil.value = null
  }

  // Renovações concorrentes (várias chamadas com 401 ao mesmo tempo) compartilham a mesma
  // promessa: o Supabase rotaciona o refresh token, então duas renovações paralelas
  // invalidariam uma à outra.
  let renovacao: Promise<boolean> | null = null
  function renovar(): Promise<boolean> {
    renovacao ??= api
      .renovar()
      .then((s) => {
        aplicar(s)
        return true
      })
      .catch(() => {
        limpar()
        return false
      })
      .finally(() => {
        renovacao = null
      })
    return renovacao
  }

  configurarSessao({
    token: () => token.value,
    renovar,
    expirou: () => {
      limpar()
      sessaoExpirada.value = true
    },
  })

  let inicializacao: Promise<void> | null = null
  function inicializar(): Promise<void> {
    inicializacao ??= renovar().then(() => {
      inicializado.value = true
    })
    return inicializacao
  }

  async function entrar(emailInformado: string, senha: string): Promise<void> {
    aplicar(await api.entrar(emailInformado, senha))
  }

  /** Retorna 'confirmar_email' quando o Supabase exige confirmação antes do login. */
  async function cadastrar(
    emailInformado: string,
    senha: string,
    ano: number,
  ): Promise<'ok' | 'confirmar_email'> {
    const r = await api.cadastrar(emailInformado, senha, ano)
    if (r.sessao) {
      aplicar(r.sessao)
      return 'ok'
    }
    return 'confirmar_email'
  }

  async function definirSerie(ano: number): Promise<void> {
    perfil.value = await api.criarPerfil(ano)
  }

  async function sair(): Promise<void> {
    try {
      await api.sair()
    } catch (e) {
      if (!(e instanceof ErroApi)) throw e
    } finally {
      limpar()
    }
  }

  return {
    token,
    usuarioId,
    email,
    perfil,
    inicializado,
    sessaoExpirada,
    autenticado,
    inicializar,
    renovar,
    entrar,
    cadastrar,
    definirSerie,
    sair,
  }
})
