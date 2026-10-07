<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import IndicadorCarregando from '../components/IndicadorCarregando.vue'
import { ErroApi } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'

const auth = useAuthStore()
const chat = useChatStore()
const router = useRouter()

const pergunta = ref('')
const lista = ref<HTMLElement | null>(null)
const anoEscolhido = ref<number | null>(null)
const erroPerfil = ref<string | null>(null)

async function enviar(): Promise<void> {
  const texto = pergunta.value
  pergunta.value = ''
  await chat.enviar(texto)
}

function teclado(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void enviar()
  }
}

async function sair(): Promise<void> {
  await auth.sair()
  chat.limpar()
  await router.replace('/login')
}

async function salvarSerie(): Promise<void> {
  if (anoEscolhido.value === null) return
  try {
    await auth.definirSerie(anoEscolhido.value)
  } catch (e) {
    erroPerfil.value = e instanceof ErroApi ? e.detalhe : 'Erro inesperado.'
  }
}

watch(
  () => [chat.mensagens.length, chat.carregando],
  async () => {
    await nextTick()
    lista.value?.scrollTo({ top: lista.value.scrollHeight, behavior: 'smooth' })
  },
)

watch(
  () => auth.autenticado,
  (ok) => {
    if (!ok) void router.replace('/login')
  },
)
</script>

<template>
  <div class="flex h-screen flex-col">
    <header class="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
      <div>
        <p class="font-bold text-slate-900">EducaChat</p>
        <p class="text-xs text-slate-500">
          {{ auth.perfil ? `Aluno do ${auth.perfil.serie}` : 'Série não definida' }}
          <span v-if="auth.email"> · {{ auth.email }}</span>
        </p>
      </div>
      <button class="text-sm font-semibold text-slate-600 hover:text-slate-900" @click="sair">
        Sair
      </button>
    </header>

    <main v-if="!auth.perfil" class="flex flex-1 items-center justify-center px-4">
      <form class="w-full max-w-sm space-y-4" @submit.prevent="salvarSerie">
        <p class="text-slate-700">Para começar, escolha sua série. Ela não poderá ser alterada.</p>
        <select v-model="anoEscolhido" required class="w-full rounded-lg border border-slate-300 px-3 py-2">
          <option :value="null" disabled>Selecione…</option>
          <option v-for="s in [6, 7, 8, 9]" :key="s" :value="s">{{ s }}º ano</option>
        </select>
        <p v-if="erroPerfil" class="text-sm text-red-600" role="alert">{{ erroPerfil }}</p>
        <button class="w-full rounded-lg bg-indigo-600 py-2 font-semibold text-white">Salvar</button>
      </form>
    </main>

    <template v-else>
      <main ref="lista" class="flex-1 space-y-4 overflow-y-auto px-4 py-6" aria-live="polite">
        <p v-if="!chat.mensagens.length" class="mx-auto max-w-md text-center text-slate-500">
          Pergunte sobre qualquer conteúdo do {{ auth.perfil.serie }}. As respostas se apoiam nas
          habilidades da BNCC da sua série.
        </p>

        <article
          v-for="m in chat.mensagens"
          :key="m.id"
          class="mx-auto max-w-2xl"
          :class="m.papel === 'aluno' ? 'flex justify-end' : ''"
        >
          <div
            v-if="m.papel === 'aluno'"
            class="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 whitespace-pre-wrap text-white"
          >
            {{ m.texto }}
          </div>
          <div
            v-else
            class="rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm ring-1"
            :class="m.erro ? 'bg-red-50 text-red-800 ring-red-200' : 'bg-white text-slate-800 ring-slate-200'"
          >
            <p class="whitespace-pre-wrap">{{ m.texto }}</p>
            <div v-if="m.habilidades?.length" class="mt-3 border-t border-slate-100 pt-2">
              <p class="mb-1 text-xs font-semibold text-slate-500">Habilidades da BNCC consultadas</p>
              <details v-for="h in m.habilidades" :key="h.codigo" class="text-xs text-slate-600">
                <summary class="cursor-pointer">
                  <span class="font-mono font-semibold text-indigo-700">{{ h.codigo }}</span>
                  · {{ h.componente }} · {{ h.serie }}
                </summary>
                <p class="mt-1 mb-2 pl-4">
                  <span class="italic">{{ h.objeto_conhecimento }}</span> — {{ h.texto }}
                </p>
              </details>
            </div>
            <p v-if="m.tempoMs" class="mt-2 text-right text-[11px] text-slate-400">
              {{ (m.tempoMs / 1000).toFixed(1) }}s
            </p>
          </div>
        </article>

        <div v-if="chat.carregando" class="mx-auto max-w-2xl">
          <IndicadorCarregando :serie="auth.perfil.serie" />
        </div>
      </main>

      <footer class="border-t border-slate-200 bg-white px-4 py-3">
        <form class="mx-auto flex max-w-2xl gap-2" @submit.prevent="enviar">
          <label for="pergunta" class="sr-only">Sua pergunta</label>
          <textarea
            id="pergunta"
            v-model="pergunta"
            rows="2"
            maxlength="2000"
            :disabled="chat.carregando"
            placeholder="Escreva sua dúvida… (Enter envia, Shift+Enter quebra linha)"
            class="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none disabled:bg-slate-100"
            @keydown="teclado"
          />
          <button
            type="submit"
            :disabled="chat.carregando || !pergunta.trim()"
            class="rounded-lg bg-indigo-600 px-4 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ chat.carregando ? 'Aguarde…' : 'Enviar' }}
          </button>
        </form>
      </footer>
    </template>
  </div>
</template>
