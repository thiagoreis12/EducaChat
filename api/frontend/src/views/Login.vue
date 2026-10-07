<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import CartaoAuth from '../components/CartaoAuth.vue'
import { ErroApi } from '../services/api'
import { destinoSeguro } from '../services/redirect'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const senha = ref('')
const enviando = ref(false)
const erro = ref<string | null>(null)

async function entrar(): Promise<void> {
  enviando.value = true
  erro.value = null
  try {
    await auth.entrar(email.value, senha.value)
    await router.replace(destinoSeguro(route.query.redirect))
  } catch (e) {
    erro.value =
      e instanceof ErroApi && e.status === 400
        ? 'E-mail ou senha incorretos.'
        : e instanceof ErroApi
          ? e.detalhe
          : 'Erro inesperado.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <CartaoAuth titulo="Entrar">
    <p
      v-if="auth.sessaoExpirada"
      class="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800"
      role="status"
    >
      Sua sessão expirou. Entre novamente.
    </p>
    <form class="space-y-4" @submit.prevent="entrar">
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
        Senha
        <input
          v-model="senha"
          type="password"
          required
          autocomplete="current-password"
          class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none"
        />
      </label>
      <p v-if="erro" class="text-sm text-red-600" role="alert">{{ erro }}</p>
      <button
        type="submit"
        :disabled="enviando"
        class="w-full rounded-lg bg-indigo-600 py-2 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
      >
        {{ enviando ? 'Entrando…' : 'Entrar' }}
      </button>
    </form>
    <p class="mt-6 text-center text-sm text-slate-600">
      Ainda não tem conta?
      <RouterLink to="/cadastro" class="font-semibold text-indigo-600 hover:underline">
        Cadastre-se
      </RouterLink>
    </p>
  </CartaoAuth>
</template>
