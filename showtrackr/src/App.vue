<template>
  <div class="min-h-screen flex flex-col">
    <AppHeader />
    <main class="flex-grow container-custom py-6">
      <TestComponent class="mt-4" />
      <!-- <router-view /> -->
    </main>
    <AppFooter />
    <Toast position="bottom-right" />
  </div>
</template>


<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

// Import components
import AppHeader from '@/components/common/AppHeader.vue'
import AppFooter from '@/components/common/AppFooter.vue'
import TestComponent from '@/components/TestComponent.vue';

// Store imports
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

onMounted(() => {
  // Initialize user preferences from local storage
  userStore.initializeFromStorage()
})
</script>