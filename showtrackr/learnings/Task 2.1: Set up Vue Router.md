# Task 2.1: Set up Vue Router

This guide walks you through setting up Vue Router for your ShowTrackr application. Vue Router enables navigation between different views and provides powerful features for building single-page applications.

## Learning Objectives

By completing this task, you will learn about:

1. **Vue Router Configuration**: Setting up router with routes and navigation
2. **Route Parameters**: Using dynamic segments in routes
3. **Navigation Guards**: Managing access and navigation flow
4. **Route Meta Fields**: Adding metadata to routes
5. **History Mode**: Understanding browser history management

## Why Vue Router?

Vue Router is the official router for Vue.js. It deeply integrates with Vue.js core to make building Single Page Applications easy. Features include:

- Nested route/view mapping
- Modular, component-based router configuration
- Route params, query, wildcards
- View transition effects powered by Vue's transition system
- Fine-grained navigation control
- Links with automatic active CSS classes
- HTML5 history mode or hash mode

## Step 1: Configure Router

Your project should already have Vue Router installed based on the initial setup. If not, install it:

```bash
npm install vue-router@4
```

### Basic Router Setup

1. Open or create `src/router/index.ts` and set up the router with routes:

```typescript
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
      // Lazy-loaded component - only loaded when needed
      component: () => import('@/views/SearchView.vue'),
      meta: {
        title: 'Search Shows - ShowTrackr',
      },
    },
    {
      path: '/show/:id',
      name: 'show-detail',
      component: () => import('@/views/ShowDetailView.vue'),
      // Route param validation - ensure id is a number
      props: (route) => ({ id: Number(route.params.id) }),
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
      // Catch-all route for 404 errors
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: {
        title: 'Page Not Found - ShowTrackr',
      },
    },
  ],
  // Scroll behavior - scroll to top on navigation or restore position
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  },
})

export default router
```

2. Apply the router to your Vue application in `src/main.ts`:

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

import './assets/styles/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
```

## Step 2: Create View Components

Next, create the view components referenced in the router configuration:

### HomeView.vue

```vue
<template>
  <DefaultLayout>
    <h1 class="text-3xl font-bold mb-6">Welcome to ShowTrackr</h1>
    <p class="text-xl mb-8">Discover, track, and manage your favorite TV shows</p>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <!-- Placeholder cards until we implement API integration -->
      <BaseCard v-for="i in 6" :key="i">
        <template #header>
          <h2 class="text-xl font-semibold">Show Title {{ i }}</h2>
        </template>
        <div class="h-40 bg-gray-200 dark:bg-gray-700 rounded flex items-center justify-center">
          <span>Show Image Placeholder</span>
        </div>
        <div class="mt-4">
          <p>
            A sample TV show description will go here. This will be replaced with real data later.
          </p>
        </div>
        <template #footer>
          <BaseButton size="sm">View Details</BaseButton>
        </template>
      </BaseCard>
    </div>
  </DefaultLayout>
</template>

<script setup lang="ts">
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
</script>
```

### NotFoundView.vue

```vue
<template>
  <DefaultLayout>
    <div class="flex flex-col items-center justify-center py-12">
      <h1 class="text-6xl font-bold text-gray-300 dark:text-gray-700">404</h1>
      <h2 class="text-2xl font-bold mb-4">Page Not Found</h2>
      <p class="text-lg mb-8 text-center">
        The page you are looking for doesn't exist or has been moved.
      </p>
      <BaseButton @click="goHome">Go Home</BaseButton>
    </div>
  </DefaultLayout>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const router = useRouter()

const goHome = () => {
  router.push({ name: 'home' })
}
</script>
```

For other view components, create placeholder files with a basic structure:

### SearchView.vue, WatchlistView.vue, DashboardView.vue

```vue
<template>
  <DefaultLayout>
    <h1 class="text-3xl font-bold mb-6">{{ pageTitle }}</h1>
    <p>This page will be implemented in a future task.</p>
  </DefaultLayout>
</template>

<script setup lang="ts">
import DefaultLayout from '@/layouts/DefaultLayout.vue'

// Change this value based on the component
const pageTitle = 'Search Shows' // or 'My Watchlist' or 'Dashboard'
</script>
```

### ShowDetailView.vue

```vue
<template>
  <DefaultLayout>
    <div v-if="id" class="mb-6">
      <h1 class="text-3xl font-bold mb-2">Show Details: {{ id }}</h1>
      <p class="text-lg">
        This page will display details for show with ID: {{ id }}. It will be fully implemented in a
        future task.
      </p>
    </div>
    <div v-else class="text-red-500">Invalid show ID</div>
    <BaseButton @click="goBack" class="mt-4">Go Back</BaseButton>
  </DefaultLayout>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

// Define props to receive the route parameter
const props = defineProps<{
  id?: number
}>()

const router = useRouter()

const goBack = () => {
  router.back()
}
</script>
```

## Step 3: Add Navigation Guards

Navigation guards are hooks provided by Vue Router that allow you to control the navigation flow. Let's add a simple guard to update the document title based on the route metadata:

```typescript
// In src/router/index.ts, add after defining the router

// Update page title based on route meta
router.beforeEach((to, from, next) => {
  document.title = (to.meta.title as string) || 'ShowTrackr'
  next()
})

// You could also add authentication guards here in the future
// router.beforeEach((to, from, next) => {
//   const isAuthenticated = checkIfUserIsAuthenticated()
//   if (to.meta.requiresAuth && !isAuthenticated) {
//     next({ name: 'login' })
//   } else {
//     next()
//   }
// })
```

## Step 4: Implement Router Links in the Layout

Update your AppHeader.vue component to use router-link for navigation:

```vue
<template>
  <header class="border-b px-4">
    <!-- ... existing header code ... -->

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

    <!-- ... rest of header code ... -->
  </header>
</template>

<script setup lang="ts">
// ... existing imports ...

const navItems = [
  { name: 'Home', path: '/' },
  { name: 'Search', path: '/search' },
  { name: 'Watchlist', path: '/watchlist' },
  { name: 'Dashboard', path: '/dashboard' },
]

// ... rest of component ...
</script>
```

## Step 5: Update App.vue to Use the Router View

Make sure your App.vue is set up to display routed components:

```vue
<template>
  <router-view v-slot="{ Component }">
    <component :is="Component" />
  </router-view>
</template>

<script setup lang="ts">
// Any app-level setup can go here
</script>
```

## Key Vue Router Concepts Explained

### 1. Route Configuration

Routes are defined as an array of objects, each with a path and a component:

```typescript
const routes = [
  { path: '/', component: Home },
  { path: '/about', component: About },
]
```

### 2. Dynamic Routes

Dynamic segments in routes are denoted by a colon:

```typescript
{ path: '/show/:id', component: ShowDetail }
```

You can access the parameter in the component with:

- `$route.params.id` (Options API)
- `useRoute().params.id` (Composition API)

### 3. Nested Routes

Routes can be nested for complex layouts:

```typescript
const routes = [
  {
    path: '/dashboard',
    component: Dashboard,
    children: [
      { path: '', component: DashboardOverview },
      { path: 'stats', component: DashboardStats },
    ],
  },
]
```

### 4. Route Props

Passing route params as component props decouples the component from the router:

```typescript
{
  path: '/show/:id',
  component: ShowDetail,
  props: true // Pass route.params as component props
}

// or with custom conversion
{
  path: '/show/:id',
  component: ShowDetail,
  props: route => ({ id: Number(route.params.id) })
}
```

### 5. Lazy Loading Routes

Lazy loading improves performance by loading components only when needed:

```typescript
{
  path: '/show/:id',
  component: () => import('@/views/ShowDetailView.vue')
}
```

### 6. Navigation Guards

Guards control navigation flow with hooks:

```typescript
// Global guard
router.beforeEach((to, from, next) => {
  // Logic here
  next() // Allow navigation
  // or
  next(false) // Cancel navigation
  // or
  next({ name: 'login' }) // Redirect
})

// Route-specific guard
{
  path: '/dashboard',
  component: Dashboard,
  beforeEnter: (to, from, next) => {
    // Logic here
    next()
  }
}

// Component-specific guard (inside component)
onBeforeRouteLeave((to, from, next) => {
  const answer = window.confirm('Are you sure you want to leave?')
  if (answer) {
    next()
  } else {
    next(false)
  }
})
```

### 7. Route Meta Fields

Meta fields can hold custom data for routes:

```typescript
{
  path: '/dashboard',
  component: Dashboard,
  meta: {
    requiresAuth: true,
    title: 'Dashboard'
  }
}
```

## Testing Your Router Setup

You can test your router by:

1. Navigating to different routes via the navigation links
2. Entering URLs directly in the browser
3. Testing the dynamic route with different IDs (e.g., /show/1, /show/2)
4. Testing the 404 page by entering a non-existent route

## Common Issues and Solutions

### Hash Mode vs. History Mode

- **Hash Mode**: URLs look like `/#/about` (works without server configuration)
- **History Mode**: Clean URLs like `/about` (requires server configuration)

For history mode to work in production, your server needs to be configured to serve the index.html for all routes. For example, in Netlify, create a `_redirects` file:

```
/* /index.html 200
```

### Route Not Found

If a route doesn't match any defined routes, it will trigger the catch-all route:

```typescript
{
  path: '/:pathMatch(.*)*',
  name: 'not-found',
  component: NotFoundView
}
```

### Component Not Rendering

Check for:

- Correct import paths
- Properly registered router in main.ts
- Correctly inserted `<router-view>` in App.vue

## Conclusion

Vue Router is a powerful tool for managing navigation in your application. With this setup, you've established:

1. A clear route structure for different pages
2. Dynamic routes for show details
3. A 404 page for non-existent routes
4. Title updates based on the current page
5. Lazy loading for better performance

In the next task, you'll build navigation components to help users navigate through these routes efficiently.

## Additional Resources

- [Vue Router Documentation](https://router.vuejs.org/)
- [Navigation Guards Guide](https://router.vuejs.org/guide/advanced/navigation-guards.html)
- [Route Meta Fields Guide](https://router.vuejs.org/guide/advanced/meta.html)
