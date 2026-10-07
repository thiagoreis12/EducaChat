/**
 * Cliente HTTP centralizado da API do EducaChat.
 *
 * - Base URL vem de VITE_API_BASE_URL (nunca hardcoded).
 * - `credentials: 'include'` para o cookie HttpOnly de refresh (só vai para /auth/*).
 * - O access token é pedido ao store de auth a cada chamada (vive só em memória).
 * - Em 401 numa rota autenticada, tenta renovar a sessão UMA vez e repete a chamada.
 */

const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')
if (!BASE) {
  throw new Error('VITE_API_BASE_URL não definida (veja frontend/.env.example)')
}

export class ErroApi extends Error {
  constructor(
    public readonly status: number,
    public readonly detalhe: string,
  ) {
    super(detalhe)
  }
}

export interface Perfil {
  ano: number
  serie: string
}

export interface Sessao {
  access_token: string
  expires_in: number
  usuario_id: string
  email: string | null
  perfil: Perfil | null
}

export interface ResultadoCadastro {
  confirmacao_pendente: boolean
  sessao: Sessao | null
}

export interface Habilidade {
  codigo: string
  serie: string
  componente: string
  objeto_conhecimento: string
  texto: string
}

/** Turno anterior da conversa, enviado no /chat para o assistente manter o contexto. */
export interface TurnoHistorico {
  papel: 'aluno' | 'assistente'
  texto: string
}

export interface RespostaChat {
  resposta: string
  serie: string
  habilidades: Habilidade[]
  tempo_ms: number
}

/** Ponte com o store de auth, configurada em runtime para evitar import circular. */
export interface ProvedorSessao {
  token(): string | null
  renovar(): Promise<boolean>
  expirou(): void
}

let provedor: ProvedorSessao | null = null
export function configurarSessao(p: ProvedorSessao | null): void {
  provedor = p
}

interface Opcoes {
  metodo?: 'GET' | 'POST'
  corpo?: unknown
  autenticado?: boolean
}

async function detalhe(resposta: Response): Promise<string> {
  try {
    const dados = await resposta.json()
    if (typeof dados?.detail === 'string') return dados.detail
    if (Array.isArray(dados?.detail)) return 'dados inválidos'
  } catch {
    /* corpo vazio ou não-JSON */
  }
  return resposta.statusText || `erro ${resposta.status}`
}

async function enviar(caminho: string, opcoes: Opcoes): Promise<Response> {
  const cabecalhos: Record<string, string> = {}
  if (opcoes.corpo !== undefined) cabecalhos['Content-Type'] = 'application/json'
  const token = opcoes.autenticado ? provedor?.token() : null
  if (token) cabecalhos.Authorization = `Bearer ${token}`
  try {
    return await fetch(BASE + caminho, {
      method: opcoes.metodo ?? 'GET',
      headers: cabecalhos,
      body: opcoes.corpo === undefined ? undefined : JSON.stringify(opcoes.corpo),
      credentials: 'include',
    })
  } catch {
    throw new ErroApi(0, 'Não foi possível conectar ao servidor.')
  }
}

export async function requisitar<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  let resposta = await enviar(caminho, opcoes)
  if (resposta.status === 401 && opcoes.autenticado && provedor) {
    if (await provedor.renovar()) {
      resposta = await enviar(caminho, opcoes)
    }
    if (resposta.status === 401) {
      provedor.expirou()
    }
  }
  if (!resposta.ok) {
    throw new ErroApi(resposta.status, await detalhe(resposta))
  }
  return (resposta.status === 204 ? undefined : await resposta.json()) as T
}

export const api = {
  cadastrar: (email: string, senha: string, ano: number) =>
    requisitar<ResultadoCadastro>('/auth/cadastro', {
      metodo: 'POST',
      corpo: { email, senha, ano },
    }),
  entrar: (email: string, senha: string) =>
    requisitar<Sessao>('/auth/login', { metodo: 'POST', corpo: { email, senha } }),
  renovar: () => requisitar<Sessao>('/auth/refresh', { metodo: 'POST' }),
  sair: () => requisitar<void>('/auth/logout', { metodo: 'POST', autenticado: true }),
  criarPerfil: (ano: number) =>
    requisitar<Perfil>('/perfil', { metodo: 'POST', corpo: { ano }, autenticado: true }),
  // A série NÃO é enviada: a API a lê do perfil a partir do token.
  chat: (pergunta: string, historico: TurnoHistorico[] = []) =>
    requisitar<RespostaChat>('/chat', {
      metodo: 'POST',
      corpo: historico.length ? { pergunta, historico } : { pergunta },
      autenticado: true,
    }),
}
