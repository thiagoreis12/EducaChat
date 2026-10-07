/** Aceita apenas caminhos internos (evita open redirect via ?redirect=https://...). */
export function destinoSeguro(valor: unknown, padrao = '/chat'): string {
  if (typeof valor !== 'string') return padrao
  if (!valor.startsWith('/') || valor.startsWith('//') || valor.includes('\\')) return padrao
  return valor
}
