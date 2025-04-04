import Aura from '@primeuix/themes/aura'
import { createApp } from 'vue'
import { createPinia } from 'pinia'

// PrimeVue imports
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'

// Import only our Tailwind-based CSS
import './assets/styles/main.css'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'

// Create the Vue app
const app = createApp(App)

// Use Pinia for state management
app.use(createPinia())

// Configure Vue Router
app.use(router)

// Configure PrimeVue
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.dark',
    },
  },
})

app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)

// Mount the app to the DOM
app.mount('#app')
