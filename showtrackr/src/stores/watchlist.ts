import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Show } from '@/models/Show'
import type { Episode } from '@/models/Episode'
import { storageService } from '@/services/storage.service'

export const useWatchlistStore = defineStore('watchlist', () => {
  // State
  const watchlist = ref<number[]>([])
  const watchedEpisodes = ref<Record<number, number[]>>({}) // showId -> episodeIds[]

  // Initialize from local storage
  function initialize() {
    const savedWatchlist = storageService.getItem('watchlist')
    if (savedWatchlist) {
      watchlist.value = JSON.parse(savedWatchlist)
    }

    const savedWatchedEpisodes = storageService.getItem('watchedEpisodes')
    if (savedWatchedEpisodes) {
      watchedEpisodes.value = JSON.parse(savedWatchedEpisodes)
    }
  }

  // Call initialize when the store is created
  initialize()

  // Getters
  const isInWatchlist = computed(() => {
    return (showId: number) => watchlist.value.includes(showId)
  })

  const isEpisodeWatched = computed(() => {
    return (showId: number, episodeId: number) => {
      return watchedEpisodes.value[showId]?.includes(episodeId) || false
    }
  })

  const getWatchedEpisodesCount = computed(() => {
    return (showId: number) => watchedEpisodes.value[showId]?.length || 0
  })

  const getWatchedPercentage = computed(() => {
    return (showId: number, totalEpisodes: number) => {
      if (!totalEpisodes) return 0
      return Math.round((getWatchedEpisodesCount.value(showId) / totalEpisodes) * 100)
    }
  })

  // Actions
  function addToWatchlist(showId: number) {
    if (!isInWatchlist.value(showId)) {
      watchlist.value.push(showId)
      saveWatchlist()
    }
  }

  function removeFromWatchlist(showId: number) {
    watchlist.value = watchlist.value.filter((id) => id !== showId)

    // Clean up watched episodes for this show
    if (watchedEpisodes.value[showId]) {
      delete watchedEpisodes.value[showId]
      saveWatchedEpisodes()
    }

    saveWatchlist()
  }

  function toggleWatchlistStatus(showId: number) {
    if (isInWatchlist.value(showId)) {
      removeFromWatchlist(showId)
    } else {
      addToWatchlist(showId)
    }
  }

  function markEpisodeAsWatched(showId: number, episodeId: number) {
    if (!watchedEpisodes.value[showId]) {
      watchedEpisodes.value[showId] = []
    }

    if (!isEpisodeWatched.value(showId, episodeId)) {
      watchedEpisodes.value[showId].push(episodeId)
      saveWatchedEpisodes()
    }
  }

  function markEpisodeAsUnwatched(showId: number, episodeId: number) {
    if (watchedEpisodes.value[showId]) {
      watchedEpisodes.value[showId] = watchedEpisodes.value[showId].filter((id) => id !== episodeId)
      saveWatchedEpisodes()
    }
  }

  function toggleEpisodeWatchedStatus(showId: number, episodeId: number) {
    if (isEpisodeWatched.value(showId, episodeId)) {
      markEpisodeAsUnwatched(showId, episodeId)
    } else {
      markEpisodeAsWatched(showId, episodeId)
    }
  }

  // Helper functions to save to localStorage
  function saveWatchlist() {
    storageService.setItem('watchlist', JSON.stringify(watchlist.value))
  }

  function saveWatchedEpisodes() {
    storageService.setItem('watchedEpisodes', JSON.stringify(watchedEpisodes.value))
  }

  return {
    // State
    watchlist,
    watchedEpisodes,

    // Getters
    isInWatchlist,
    isEpisodeWatched,
    getWatchedEpisodesCount,
    getWatchedPercentage,

    // Actions
    initialize,
    addToWatchlist,
    removeFromWatchlist,
    toggleWatchlistStatus,
    markEpisodeAsWatched,
    markEpisodeAsUnwatched,
    toggleEpisodeWatchedStatus,
  }
})
