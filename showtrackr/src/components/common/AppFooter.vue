<template>
    <footer class="shadow-inner py-6  px-4">
      <div class="container-custom">
        <div class="flex flex-col md:flex-row justify-between items-center">
          <div class="text-center md:text-left mb-4 md:mb-0">
            <div class="text-lg font-semibold text-primary">ShowTrackr</div>
            <div class="text-sm text-text-light dark:text-gray-400">
              Track your favorite TV shows
            </div>
          </div>
          
          <div class="flex flex-col items-center md:items-end">
            <div class="text-sm text-text-light dark:text-gray-400">
              Data provided by <a href="https://www.tvmaze.com/api" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">TVMaze API</a>
            </div>
            <div class="text-sm text-text-light dark:text-gray-400 mt-1">
              &copy; {{ currentYear }} ShowTrackr. All rights reserved.
            </div>
          </div>
        </div>
      </div>
    </footer>
  </template>
  
  <script setup lang="ts">
  import { computed } from 'vue'
  
  const currentYear = computed(() => new Date().getFullYear())
  </script>