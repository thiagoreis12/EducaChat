<script setup lang="ts">
defineProps<{ titulo: string }>()
</script>

<template>
  <main class="flex min-h-screen items-center justify-center px-4">
    <section class="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
      <p class="text-sm font-semibold text-indigo-600">EducaChat</p>
      <h1 class="mt-1 mb-6 text-2xl font-bold text-slate-900">{{ titulo }}</h1>
      <slot />
    </section>
  </main>
</template>
