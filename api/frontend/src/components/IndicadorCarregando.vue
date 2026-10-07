<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{ serie: string }>()

// O protótipo tem latência extra (recuperação na BNCC + LLM): a UI mostra a etapa e o
// tempo decorrido para o aluno não achar que travou.
const segundos = ref(0)
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => (segundos.value += 1), 1000)
})
onBeforeUnmount(() => clearInterval(timer))

const etapa = computed(() => {
  if (segundos.value < 2) return `Buscando habilidades da BNCC do ${props.serie}…`
  if (segundos.value < 20) return 'Escrevendo a resposta…'
  return 'Ainda trabalhando: às vezes o assistente demora um pouco mais.'
})
</script>

<template>
  <div class="flex items-center gap-3 text-sm text-slate-600" role="status" aria-live="polite">
    <span class="flex gap-1" aria-hidden="true">
      <span class="h-2 w-2 animate-bounce rounded-full bg-indigo-500 [animation-delay:-0.3s]" />
      <span class="h-2 w-2 animate-bounce rounded-full bg-indigo-500 [animation-delay:-0.15s]" />
      <span class="h-2 w-2 animate-bounce rounded-full bg-indigo-500" />
    </span>
    <span>{{ etapa }}</span>
    <span class="tabular-nums text-slate-400">{{ segundos }}s</span>
  </div>
</template>
