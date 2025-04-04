import { defineStore } from 'pinia'
import { ref } from 'vue'
import { storageService } from '@/services/storage.service'

export const useUserStore = defineStore('user', () => {
  // State
  const isDarkMode = ref(false)
  const sortPreference = ref<string>('name') // 'name', 'date', 'rating'
  const filterPreference = ref<string>('all') // 'all', 'watching', 'completed', 'planned'
  const lastVisitedShows = ref<number[]>([])

  // Initialize from local storage
  function initializeFromStorage() {
    // Dark mode preference
    const savedDarkMode = storageService.getItem('darkMode')
    if (savedDarkMode !== null) {
      isDarkMode.value = JSON.parse(savedDarkMode)
      applyTheme()
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      isDarkMode.value = prefersDark
      applyTheme()
    }

    // Sort preference
    const savedSortPreference = storageService.getItem('sortPreference')
    if (savedSortPreference) {
      sortPreference.value = savedSortPreference
    }

    // Filter preference
    const savedFilterPreference = storageService.getItem('filterPreference')
    if (savedFilterPreference) {
      filterPreference.value = savedFilterPreference
    }

    // Last visited shows
    const savedLastVisitedShows = storageService.getItem('lastVisitedShows')
    if (savedLastVisitedShows) {
      lastVisitedShows.value = JSON.parse(savedLastVisitedShows)
    }
  }

  // Actions
  function toggleDarkMode() {
    isDarkMode.value = !isDarkMode.value
    storageService.setItem('darkMode', JSON.stringify(isDarkMode.value))
    applyTheme()
  }

  function setSortPreference(preference: string) {
    sortPreference.value = preference
    storageService.setItem('sortPreference', preference)
  }

  function setFilterPreference(preference: string) {
    filterPreference.value = preference
    storageService.setItem('filterPreference', preference)
  }

  function addToLastVisited(showId: number) {
    // Remove if already exists
    lastVisitedShows.value = lastVisitedShows.value.filter((id) => id !== showId)

    // Add to front
    lastVisitedShows.value.unshift(showId)

    // Keep only the last 10
    if (lastVisitedShows.value.length > 10) {
      lastVisitedShows.value = lastVisitedShows.value.slice(0, 10)
    }

    storageService.setItem('lastVisitedShows', JSON.stringify(lastVisitedShows.value))
  }

  // Helper function to apply theme to HTML element
  function applyTheme() {
    if (isDarkMode.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  return {
    // State
    isDarkMode,
    sortPreference,
    filterPreference,
    lastVisitedShows,

    // Actions
    initializeFromStorage,
    toggleDarkMode,
    setSortPreference,
    setFilterPreference,
    addToLastVisited,
  }
})
