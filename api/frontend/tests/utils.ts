import { vi } from 'vitest'

export interface Chamada {
  url: string
  metodo: string
  corpo: unknown
  auth: string | null
  credentials: RequestCredentials | undefined
}

type Rota = (c: Chamada) => { status: number; corpo?: unknown }

/** Substitui fetch por um roteador simples e registra as chamadas. */
export function mockFetch(rotas: Record<string, Rota>): Chamada[] {
  const chamadas: Chamada[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const headers = (init.headers ?? {}) as Record<string, string>
      const c: Chamada = {
        url: url.replace('http://api.teste', ''),
        metodo: init.method ?? 'GET',
        corpo: init.body ? JSON.parse(init.body as string) : undefined,
        auth: headers.Authorization ?? null,
        credentials: init.credentials,
      }
      chamadas.push(c)
      const rota = rotas[`${c.metodo} ${c.url}`]
      const r = rota ? rota(c) : { status: 404, corpo: { detail: 'não mapeado' } }
      return new Response(r.corpo === undefined ? null : JSON.stringify(r.corpo), {
        status: r.status,
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
  return chamadas
}

export function sessao(token: string, ano: number | null = 6) {
  return {
    access_token: token,
    expires_in: 3600,
    usuario_id: 'u1',
    email: 'a@escola.br',
    perfil: ano === null ? null : { ano, serie: `${ano}º ano` },
  }
}
