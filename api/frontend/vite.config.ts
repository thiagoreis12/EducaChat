/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: { host: 'localhost', port: 5173, strictPort: true },
  test: { environment: 'happy-dom', env: { VITE_API_BASE_URL: 'http://api.teste' } },
})
