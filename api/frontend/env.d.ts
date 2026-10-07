/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL base da API FastAPI, ex.: http://localhost:8000 (sem barra no fim). */
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const componente: DefineComponent<object, object, unknown>
  export default componente
}
