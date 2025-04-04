<template>
  <div>
    <section class="py-12 bg-primary bg-opacity-10 dark:bg-gray-900 rounded-lg mb-12">
      <div class="text-center">
        <h1 class="text-4xl font-bold text-text-dark dark:text-white mb-4">
          Track Your Favorite Shows
        </h1>
        <p class="text-xl text-text-light dark:text-gray-300 mb-8 max-w-3xl mx-auto">
          Keep up with episodes, manage your watchlist, and see your viewing stats all in one place.
        </p>
        <div class="flex flex-wrap justify-center gap-4">
          <router-link to="/search" class="btn btn-primary inline-flex items-center">
            <i class="pi pi-search mr-2"></i> Find Shows
          </router-link>
          <router-link to="/watchlist" class="btn bg-white text-primary border border-primary hover:bg-gray-100 dark:bg-gray-800 dark:text-primary-light dark:border-primary-light dark:hover:bg-gray-700 inline-flex items-center">
            <i class="pi pi-list mr-2"></i> View Watchlist
          </router-link>
        </div>
      </div>
    </section>

    <!-- Recently Visited Shows -->
    <section v-if="recentlyVisitedShows.length > 0" class="mb-12">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-text-dark dark:text-white">Recently Visited</h2>
        <router-link to="/search" class="text-primary hover:underline dark:text-primary-light">
          Find more shows
        </router-link>
      </div>
      
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        <div v-for="show in recentlyVisitedShows" :key="show.id" class="animate-fade-in">
          <!-- This will be replaced with a proper ShowCard component later -->
          <div class="card h-full flex flex-col">
            <div class="relative pb-[140%] mb-4 overflow-hidden rounded-md bg-gray-200 dark:bg-gray-700">
              <img 
                v-if="show.image?.medium" 
                :src="show.image.medium" 
                :alt="show.name" 
                class="absolute inset-0 w-full h-full object-cover"
              />
              <div v-else class="absolute inset-0 flex items-center justify-center">
                <i class="pi pi-image text-4xl text-gray-400"></i>
              </div>
            </div>
            
            <div class="flex-grow">
              <h3 class="text-lg font-semibold mb-1 text-text-dark dark:text-white">
                {{ show.name }}
              </h3>
              <div class="flex items-center mb-2">
                <span v-if="show.rating?.average" class="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100 px-2 py-0.5 rounded text-sm font-medium">
                  {{ show.rating.average }}
                </span>
                <span v-if="show.premiered" class="text-sm text-text-light dark:text-gray-400 ml-auto">
                  {{ new Date(show.premiered).getFullYear() }}
                </span>
              </div>
            </div>
            
            <router-link 
              :to="`/show/${show.id}`" 
              class="mt-2 inline-flex items-center text-primary hover:underline dark:text-primary-light font-medium"
            >
              View Details <i class="pi pi-arrow-right ml-1"></i>
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- Popular Shows (static for now) -->
    <section>
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-text-dark dark:text-white">Popular Shows</h2>
        <router-link to="/search" class="text-primary hover:underline dark:text-primary-light">
          View all
        </router-link>
      </div>
      
      <div class="bg-gray-100 dark:bg-gray-800 p-8 rounded-lg text-center">
        <p class="text-text-light dark:text-gray-300 mb-4">
          Your popular shows will appear here once you start tracking shows.
        </p>
        <router-link to="/search" class="btn btn-primary inline-flex items-center">
          <i class="pi pi-search mr-2"></i> Find Shows
        </router-link>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { useShowsStore } from '@/stores/shows'
import type { Show } from '@/models/Show'

const userStore = useUserStore()
const showsStore = useShowsStore()

const recentlyVisitedShows = ref<Show[]>([])
const isLoading = ref(false)

onMounted(async () => {
  if (userStore.lastVisitedShows.length > 0) {
    isLoading.value = true
    
    try {
      // Fetch details for recently visited shows
      const showPromises = userStore.lastVisitedShows.slice(0, 4).map(id => 
        showsStore.fetchShowDetails(id)
      )
      
      const shows = await Promise.all(showPromises)
      recentlyVisitedShows.value = shows.filter(show => show !== null) as Show[]
    } catch (error) {
      console.error('Error fetching recently visited shows:', error)
    } finally {
      isLoading.value = false
    }
  }
})
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.5s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>