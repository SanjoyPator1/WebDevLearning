<template>
    <header class="bg-white shadow dark:bg-gray-800">
      <div class="container-custom flex items-center justify-between h-16">
        <!-- Logo and App Name -->
        <div class="flex items-center">
          <router-link to="/" class="flex items-center">
            <span class="text-primary text-2xl font-bold">ShowTrackr</span>
          </router-link>
        </div>
        
        <!-- Navigation -->
        <nav class="hidden md:flex space-x-6">
          <router-link 
            v-for="item in navItems" 
            :key="item.name" 
            :to="item.path"
            class="text-text-dark hover:text-primary dark:text-gray-300 dark:hover:text-white transition-colors"
            active-class="text-primary dark:text-white font-medium"
          >
            {{ item.name }}
          </router-link>
        </nav>
        
        <!-- Search and Dark Mode Toggle -->
        <div class="flex items-center space-x-4">
          <router-link 
            to="/search" 
            class="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Search shows"
          >
            <i class="pi pi-search text-text-dark dark:text-gray-300"></i>
          </router-link>
          
          <button 
            @click="toggleDarkMode"
            class="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Toggle dark mode"
          >
            <i :class="['pi', userStore.isDarkMode ? 'pi-sun' : 'pi-moon', 'text-text-dark dark:text-gray-300']"></i>
          </button>
          
          <!-- Mobile Menu Button -->
          <button 
            @click="isMobileMenuOpen = !isMobileMenuOpen"
            class="md:hidden p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Open mobile menu"
          >
            <i class="pi pi-bars text-text-dark dark:text-gray-300"></i>
          </button>
        </div>
      </div>
      
      <!-- Mobile Menu -->
      <div 
        v-if="isMobileMenuOpen" 
        class="md:hidden bg-white dark:bg-gray-800 shadow-lg"
      >
        <div class="container-custom py-4 space-y-3">
          <router-link 
            v-for="item in navItems" 
            :key="item.name" 
            :to="item.path"
            class="block py-2 text-text-dark hover:text-primary dark:text-gray-300 dark:hover:text-white transition-colors"
            active-class="text-primary dark:text-white font-medium"
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
  
  const userStore = useUserStore()
  
  const isMobileMenuOpen = ref(false)
  
  const navItems = [
    { name: 'Home', path: '/' },
    { name: 'Watchlist', path: '/watchlist' },
    { name: 'Dashboard', path: '/dashboard' }
  ]
  
  const toggleDarkMode = () => {
    userStore.toggleDarkMode()
  }
  </script>