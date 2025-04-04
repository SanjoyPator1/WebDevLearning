import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: {
        title: 'Home - ShowTrackr',
      },
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/SearchView.vue'),
      meta: {
        title: 'Search Shows - ShowTrackr',
      },
    },
    {
      path: '/show/:id',
      name: 'show-detail',
      component: () => import('@/views/ShowDetailView.vue'),
      meta: {
        title: 'Show Details - ShowTrackr',
      },
    },
    {
      path: '/watchlist',
      name: 'watchlist',
      component: () => import('@/views/WatchlistView.vue'),
      meta: {
        title: 'My Watchlist - ShowTrackr',
      },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: {
        title: 'Dashboard - ShowTrackr',
      },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: {
        title: 'Page Not Found - ShowTrackr',
      },
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  },
})

// Update page title based on route meta
router.beforeEach((to, from, next) => {
  document.title = (to.meta.title as string) || 'ShowTrackr'
  next()
})

export default router
