import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { criarRouter } from './router'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(criarRouter())
app.mount('#app')
