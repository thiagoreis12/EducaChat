<script setup>
import { onMounted, ref } from 'vue'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8001'
const apiStatus = ref('checando')
const apiDetail = ref('')

onMounted(async () => {
  try {
    const response = await fetch(`${apiUrl}/health`)
    if (!response.ok) {
      apiStatus.value = 'erro'
      apiDetail.value = `HTTP ${response.status}`
      return
    }
    const body = await response.json()
    apiStatus.value = body.status === 'ok' ? 'ok' : 'erro'
    apiDetail.value = JSON.stringify(body)
  } catch (error) {
    apiStatus.value = 'offline'
    apiDetail.value = error instanceof Error ? error.message : 'falha ao conectar'
  }
})
</script>

<template>
  <main class="min-h-screen bg-slate-50 text-slate-800">
    <div class="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6 py-16">
      <p class="text-sm font-medium tracking-wide text-slate-500">ETEP · EXPOETEP 2026.2</p>
      <h1 class="mt-2 text-3xl font-semibold text-slate-900">EducaChat</h1>
      <p class="mt-3 text-slate-600">
        Tutoria socrática para alunos a partir do 6º ano. Matemática, Português,
        Ciências e conhecimentos gerais.
      </p>

      <section class="mt-8 rounded-lg border border-slate-200 bg-white p-4">
        <h2 class="text-sm font-medium text-slate-500">API</h2>
        <p v-if="apiStatus === 'checando'" class="mt-1 text-slate-700">Verificando /health…</p>
        <p v-else-if="apiStatus === 'ok'" class="mt-1 text-emerald-700">
          Ligada — {{ apiDetail }}
        </p>
        <p v-else class="mt-1 text-amber-800">
          {{ apiStatus === 'offline' ? 'Não alcançada' : 'Resposta inesperada' }}
          — {{ apiDetail }}
        </p>
        <p class="mt-2 text-xs text-slate-500">{{ apiUrl }}/health</p>
      </section>
    </div>
  </main>
</template>
