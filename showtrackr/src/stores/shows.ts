import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Show, SearchResult } from '@/models/Show'
import { tvMazeService } from '@/services/tvmaze.service'

export const useShowsStore = defineStore('shows', () => {
  // State
  const shows = ref<Show[]>([])
  const currentShow = ref<Show | null>(null)
  const searchResults = ref<SearchResult[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const getShowById = computed(() => {
    return (id: number) => shows.value.find((show) => show.id === id)
  })

  // Actions
  async function searchShows(query: string) {
    if (!query.trim()) return

    isLoading.value = true
    error.value = null

    try {
      searchResults.value = await tvMazeService.searchShows(query)
    } catch (err) {
      error.value = 'Failed to search shows. Please try again.'
      console.error('Error searching shows:', err)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchShowDetails(id: number) {
    isLoading.value = true
    error.value = null

    try {
      const show = await tvMazeService.getShowById(id)
      currentShow.value = show

      // Add to shows array if not already present
      if (!shows.value.some((s) => s.id === show.id)) {
        shows.value.push(show)
      }

      return show
    } catch (err) {
      error.value = 'Failed to fetch show details. Please try again.'
      console.error('Error fetching show details:', err)
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function fetchShowEpisodes(showId: number) {
    isLoading.value = true
    error.value = null

    try {
      return await tvMazeService.getShowEpisodes(showId)
    } catch (err) {
      error.value = 'Failed to fetch episodes. Please try again.'
      console.error('Error fetching episodes:', err)
      return []
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    shows,
    currentShow,
    searchResults,
    isLoading,
    error,

    // Getters
    getShowById,

    // Actions
    searchShows,
    fetchShowDetails,
    fetchShowEpisodes,
  }
})
