# Task 1.3: Create Layout Components

This guide will walk you through creating layout components for your ShowTrackr application. Layouts provide consistent structure across different pages and allow for better component organization.

## Learning Objectives

By completing this task, you will learn about:

1. **Component Composition**: Building larger components from smaller ones
2. **Named Slots**: Using multiple slots for content distribution
3. **Layout Patterns**: Common layout structures in web applications
4. **Dynamic Layouts**: Switching layouts based on routes

## Components to Create

You'll be creating three layout-related components:

1. **DefaultLayout.vue**: The main layout with header and footer
2. **AppHeader.vue**: Site header with navigation
3. **AppFooter.vue**: Site footer with information

## 1. AppHeader.vue

### Concepts to Apply

- **Navigation**: Links to different sections of the site
- **Responsive Design**: Mobile-friendly menu
- **Dark Mode Toggle**: Toggle for light/dark theme
- **User Preferences**: Integration with user store

### Implementation Steps

1. Create a new file at `src/components/common/AppHeader.vue`
2. Implement a component with:
   - Logo and site title
   - Navigation links
   - Dark mode toggle
   - Mobile menu

### Example Implementation

```vue
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
```

## 2. AppFooter.vue

### Concepts to Apply

- **Static Content**: Copyright and information
- **External Links**: Links to external resources
- **Year Calculation**: Dynamic copyright year

### Implementation Steps

1. Create a new file at `src/components/common/AppFooter.vue`
2. Implement a component with:
   - Copyright information
   - App information
   - External links

### Example Implementation

```vue
<template>
  <footer class="shadow-inner py-6 px-4">
    <div class="container-custom">
      <div class="flex flex-col md:flex-row justify-between items-center">
        <div class="text-center md:text-left mb-4 md:mb-0">
          <div class="text-lg font-semibold text-primary">ShowTrackr</div>
          <div class="text-sm text-text-light dark:text-gray-400">Track your favorite TV shows</div>
        </div>

        <div class="flex flex-col items-center md:items-end">
          <div class="text-sm text-text-light dark:text-gray-400">
            Data provided by
            <a
              href="https://www.tvmaze.com/api"
              target="_blank"
              rel="noopener noreferrer"
              class="text-primary hover:underline"
              >TVMaze API</a
            >
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
```

## 3. DefaultLayout.vue

### Concepts to Apply

- **Layout Structure**: Header, main content, footer
- **Slot Distribution**: Using slots for flexible content placement
- **Consistent UI**: Maintaining consistent UI across pages

### Implementation Steps

1. Create a new file at `src/layouts/DefaultLayout.vue`
2. Implement a component with:
   - AppHeader component
   - Slot for main content
   - AppFooter component

### Example Implementation

```vue
<template>
  <div class="flex flex-col min-h-screen">
    <AppHeader />

    <main class="flex-grow container-custom py-6 px-4">
      <!-- The slot allows page content to be injected here -->
      <slot></slot>
    </main>

    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/common/AppHeader.vue'
import AppFooter from '@/components/common/AppFooter.vue'
</script>

<style scoped>
.container-custom {
  @apply max-w-7xl mx-auto w-full;
}
</style>
```

## 4. DashboardLayout.vue (Optional Extra)

For your dashboard, you might want a different layout with a sidebar:

```vue
<template>
  <div class="flex flex-col min-h-screen">
    <AppHeader />

    <div class="flex-grow flex flex-col md:flex-row">
      <!-- Sidebar -->
      <aside class="w-full md:w-64 bg-gray-100 dark:bg-gray-800 md:min-h-screen">
        <div class="p-4">
          <h2 class="text-lg font-semibold mb-4">Dashboard</h2>
          <nav class="space-y-2">
            <router-link
              v-for="item in sidebarItems"
              :key="item.name"
              :to="item.path"
              class="block py-2 px-4 rounded-lg transition-colors hover:bg-gray-200 dark:hover:bg-gray-700"
              active-class="bg-primary text-white hover:bg-primary-dark"
            >
              {{ item.name }}
            </router-link>
          </nav>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="flex-grow p-6">
        <slot></slot>
      </main>
    </div>

    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/common/AppHeader.vue'
import AppFooter from '@/components/common/AppFooter.vue'

const sidebarItems = [
  { name: 'Overview', path: '/dashboard' },
  { name: 'Statistics', path: '/dashboard/statistics' },
  { name: 'Recent Shows', path: '/dashboard/recent' },
  { name: 'Viewing Progress', path: '/dashboard/progress' },
]
</script>
```

## 5. Integrating Layouts in App.vue

To use these layouts in your application, you need to update the `App.vue` file:

```vue
<template>
  <router-view v-slot="{ Component }">
    <component :is="Component" />
  </router-view>
  <Toast position="bottom-right" />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onMounted(() => {
  // Initialize user preferences from local storage
  userStore.initializeFromStorage()
})
</script>
```

## 6. Using Layouts with Pages

To use layouts with your pages, you'll need to modify your page components. Here's how to use the DefaultLayout:

```vue
<template>
  <DefaultLayout>
    <h1 class="text-2xl font-bold mb-4">Home Page</h1>
    <p>This is the home page content wrapped in the default layout.</p>
  </DefaultLayout>
</template>

<script setup lang="ts">
import DefaultLayout from '@/layouts/DefaultLayout.vue'
</script>
```

And for dashboard pages:

```vue
<template>
  <DashboardLayout>
    <h1 class="text-2xl font-bold mb-4">Dashboard</h1>
    <p>This is the dashboard content with a specialized layout.</p>
  </DashboardLayout>
</template>

<script setup lang="ts">
import DashboardLayout from '@/layouts/DashboardLayout.vue'
</script>
```

## Key Vue.js Concepts Explained

### 1. Component Composition

Component composition is about building complex UIs by combining smaller, reusable components. In this task, we've created layout components that include other components:

```vue
<template>
  <div>
    <AppHeader />
    <main><slot></slot></main>
    <AppFooter />
  </div>
</template>
```

This pattern allows for:

- Better organization of code
- Reuse of common elements
- Clearer separation of concerns

### 2. Named Slots

Named slots allow you to define multiple insertion points in a component. This is particularly useful for layouts:

```vue
<template>
  <div>
    <header>
      <slot name="header">Default header content</slot>
    </header>
    <main>
      <slot>Default main content</slot>
    </main>
    <footer>
      <slot name="footer">Default footer content</slot>
    </footer>
  </div>
</template>
```

Usage in parent component:

```vue
<ComplexLayout>
  <template #header>Custom Header</template>
  <div>Main Content</div>
  <template #footer>Custom Footer</template>
</ComplexLayout>
```

### 3. Layout Patterns

Common layout patterns in web applications include:

- **Default Layout**: Header, content area, footer
- **Dashboard Layout**: Header, sidebar, content area, footer
- **Auth Layout**: Simplified layout for login/signup pages
- **Empty Layout**: No header/footer, used for fullscreen or special pages

### 4. Dynamic Layouts

Vue Router allows you to use different layouts based on the route:

```vue
<template>
  <component :is="layout">
    <router-view />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import DashboardLayout from '@/layouts/DashboardLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'

const route = useRoute()
const layout = computed(() => {
  // Get layout from route meta or default to DefaultLayout
  const layoutName = route.meta.layout || 'default'

  switch (layoutName) {
    case 'dashboard':
      return DashboardLayout
    case 'auth':
      return AuthLayout
    default:
      return DefaultLayout
  }
})
</script>
```

With this approach, you can specify the layout in the route definition:

```typescript
const routes = [
  {
    path: '/dashboard',
    component: DashboardView,
    meta: { layout: 'dashboard' },
  },
  {
    path: '/login',
    component: LoginView,
    meta: { layout: 'auth' },
  },
]
```

## CSS Container Classes

For consistent container behavior, consider adding these utility classes:

```css
/* In your main CSS file or as a scoped style in layouts */
.container-custom {
  @apply max-w-7xl mx-auto w-full px-4;
}
```

## Conclusion

By creating layout components, you've established a consistent structure for your application pages. This approach offers several benefits:

1. **Consistency**: All pages using the same layout will have a consistent look and feel
2. **DRY Principle**: You don't have to repeat header and footer code on every page
3. **Maintainability**: When you need to update the header or footer, you only need to change it in one place
4. **Flexibility**: Different types of pages can use different layouts as needed

These layout components form the structural foundation of your application. They provide the frame within which all your other components will be displayed. As your application grows, you might need to create additional specialized layouts, but the basic pattern will remain the same.

## Testing Your Layout Components

To test your layout components, you can create a simple page that uses them:

```vue
<template>
  <DefaultLayout>
    <div class="space-y-8">
      <section>
        <h1 class="text-3xl font-bold mb-4">Layout Test Page</h1>
        <p class="text-lg">
          This page demonstrates the DefaultLayout component with header and footer.
        </p>
      </section>

      <section class="bg-gray-100 dark:bg-gray-800 p-6 rounded-lg">
        <h2 class="text-xl font-semibold mb-2">Content Section</h2>
        <p>
          This content is placed within the main slot of the DefaultLayout. The layout handles the
          header and footer automatically.
        </p>
      </section>
    </div>
  </DefaultLayout>
</template>

<script setup lang="ts">
import DefaultLayout from '@/layouts/DefaultLayout.vue'
</script>
```

## Next Steps

After completing this task, you will have:

- Created a header component with navigation and responsive design
- Built a footer component with copyright and information
- Implemented layout components that use these elements
- Understood how to nest components and use slots effectively

In the next phase, you'll set up Vue Router to handle navigation between different pages, which will build on the layout structure you've established here.

## Advanced Topics to Explore

- **Route-based layout switching**: Dynamically select layouts based on the current route
- **Nested layouts**: Create layouts within layouts for more complex page structures
- **Transitions**: Add page transition animations when switching between routes
- **Sticky headers/footers**: Implement fixed positioning for headers or footers
- **Collapsible sidebars**: Create expandable/collapsible sidebar navigation

With your layout components in place, you've completed Phase 1 of the roadmap and established a solid foundation for your ShowTrackr application!
