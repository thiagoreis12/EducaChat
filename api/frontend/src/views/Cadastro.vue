<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import CartaoAuth from '../components/CartaoAuth.vue'
import { ErroApi } from '../services/api'
import { useAuthStore } from '../stores/auth'

const SERIES = [6, 7, 8, 9] as const

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const senha = ref('')
const ano = ref<number | null>(null)
const enviando = ref(false)
const erro = ref<string | null>(null)
const confirmarEmail = ref(false)

async function cadastrar(): Promise<void> {
  if (ano.value === null) {
    erro.value = 'Escolha sua série.'
    return
  }
  enviando.value = true
  erro.value = null
  try {
    const r = await auth.cadastrar(email.value, senha.value, ano.value)
    if (r === 'confirmar_email') {
      confirmarEmail.value = true
    } else {
      await router.replace('/chat')
    }
  } catch (e) {
    erro.value = e instanceof ErroApi ? e.detalhe : 'Erro inesperado.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <CartaoAuth titulo="Criar conta">
    <div v-if="confirmarEmail" class="space-y-4 text-sm text-slate-700" role="status">
      <p>
        Enviamos um link de confirmação para <strong>{{ email }}</strong>. Confirme o e-mail e
        depois entre.
      </p>
      <RouterLink to="/login" class="font-semibold text-indigo-600 hover:underline">
        Ir para o login
      </RouterLink>
    </div>
    <form v-else class="space-y-4" @submit.prevent="cadastrar">
      <label class="block text-sm font-medium text-slate-700">
        E-mail
        <input
          v-model="email"
          type="email"
          required
          autocomplete="email"
          class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none"
        />
      </label>
      <label class="block text-sm font-medium text-slate-700">
        Senha (mínimo 6 caracteres)
        <input
          v-model="senha"
          type="password"
          required
          minlength="6"
          autocomplete="new-password"
          class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none"
        />
      </label>
      <fieldset>
        <legend class="text-sm font-medium text-slate-700">Sua série</legend>
        <div class="mt-2 grid grid-cols-4 gap-2">
          <label
            v-for="s in SERIES"
            :key="s"
            class="cursor-pointer rounded-lg border px-2 py-2 text-center text-sm"
            :class="
              ano === s
                ? 'border-indigo-600 bg-indigo-50 font-semibold text-indigo-700'
                : 'border-slate-300 text-slate-700'
            "
          >
            <input v-model="ano" type="radio" name="serie" :value="s" class="sr-only" />
            {{ s }}º ano
          </label>
        </div>
        <p class="mt-2 text-xs text-slate-500">A série não pode ser alterada depois.</p>
      </fieldset>
      <p v-if="erro" class="text-sm text-red-600" role="alert">{{ erro }}</p>
      <button
        type="submit"
        :disabled="enviando"
        class="w-full rounded-lg bg-indigo-600 py-2 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
      >
        {{ enviando ? 'Criando conta…' : 'Criar conta' }}
      </button>
    </form>
    <p class="mt-6 text-center text-sm text-slate-600">
      Já tem conta?
      <RouterLink to="/login" class="font-semibold text-indigo-600 hover:underline">Entrar</RouterLink>
    </p>
  </CartaoAuth>
</template>
