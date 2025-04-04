<template>
  <header class="border-b px-4">
    <div class="container-custom flex items-center justify-between h-16">
      <!-- Logo and App Name -->
      <div class="flex items-center">
        <router-link to="/" class="flex items-center">
          <img :src="LOGOS.ICON_ONLY" alt="ShowTrackr Logo" class="h-10 w-auto" />
        </router-link>
      </div>

      <!-- Navigation -->
      <nav class="hidden md:flex space-x-6">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="item.path"
          class="opacity-65 transition-colors"
          active-class="font-semibold opacity-100"
        >
          {{ item.name }}
        </router-link>
      </nav>

      <!-- Search and Dark Mode Toggle -->
      <div class="flex items-center space-x-4">
        <router-link
          to="/search"
          class="p-2 rounded-full transition-colors"
          aria-label="Search shows"
        >
          <i class="pi pi-search text-text-dark dark:text-gray-300"></i>
        </router-link>

        <button
          @click="toggleDarkMode"
          class="p-2 rounded-full transition-colors"
          aria-label="Toggle dark mode"
        >
          <i
            :class="[
              'pi',
              userStore.isDarkMode ? 'pi-sun' : 'pi-moon',
              'text-text-dark dark:text-gray-300',
            ]"
          ></i>
        </button>

        <!-- Mobile Menu Button -->
        <button
          @click="isMobileMenuOpen = !isMobileMenuOpen"
          class="md:hidden p-2 rounded-full transition-colors"
          aria-label="Open mobile menu"
        >
          <i class="pi pi-bars text-text-dark dark:text-gray-300"></i>
        </button>
      </div>
    </div>

    <!-- Mobile Menu -->
    <div v-if="isMobileMenuOpen" class="md:hidden">
      <div class="py-4 space-y-3">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="item.path"
          class="block py-2 opacity-65 transition-colors"
          active-class="font-semibold opacity-100"
          @click="isMobileMenuOpen = false"
        >
          {{ item.name }}
        </router-link>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { LOGOS } from '@/utils/constants/images'

const userStore = useUserStore()

const isMobileMenuOpen = ref(false)

const navItems = [
  { name: 'Home', path: '/' },
  { name: 'Watchlist', path: '/watchlist' },
  { name: 'Dashboard', path: '/dashboard' },
]

const toggleDarkMode = () => {
  userStore.toggleDarkMode()
}
</script>
