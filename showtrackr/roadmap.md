# ShowTrackr Vue.js Learning Roadmap

Welcome to the ShowTrackr project! This roadmap will guide you through building a TV show tracking application while learning Vue.js 3 concepts incrementally. Each task builds on previous ones, introducing new Vue.js features and best practices.

## Project Overview

ShowTrackr is a web application that allows users to:

- Discover TV shows
- Track shows they're watching
- Mark episodes as watched
- See statistics about their viewing habits
- Create and manage a watchlist

## Technology Stack

- **Vue.js 3** with Composition API
- **TypeScript** for type safety
- **Pinia** for state management
- **Vue Router** for navigation
- **Tailwind CSS** for styling
- **Vite** for build tooling
- **TVMaze API** for show data

## Learning Roadmap

### Phase 1: Project Setup and Fundamentals

#### Task 1.1: Project Initialization and Configuration

- [x] Install and set up the Vue.js project with Vite
- [x] Configure TypeScript, ESLint, and Prettier
- [x] Set up Tailwind CSS
- [x] Configure basic folder structure
- **Learning Focus**: Project setup, Vue 3 with Vite, TypeScript integration

#### Task 1.2: Create Base UI Components

- [ ] Implement BaseButton.vue (props, slots, events)
- [ ] Implement BaseCard.vue (slots, styling props)
- [ ] Implement BaseLoader.vue (conditional rendering)
- **Learning Focus**: Vue component basics, props, slots, conditional rendering

#### Task 1.3: Create Layout Components

- [ ] Implement DefaultLayout.vue
- [ ] Create AppHeader.vue and AppFooter.vue
- [ ] Integrate layouts into App.vue
- **Learning Focus**: Component composition, named slots, layout patterns

### Phase 2: Routing and Navigation

#### Task 2.1: Set up Vue Router

- [ ] Configure router in router/index.ts
- [ ] Implement basic routes for Home, Search, and NotFound views
- [ ] Add navigation guards for routes
- **Learning Focus**: Vue Router, navigation guards, route params

#### Task 2.2: Implement Navigation Components

- [ ] Create AppSidebar.vue with navigation links
- [ ] Implement active route highlighting
- [ ] Add responsive menu for mobile
- **Learning Focus**: Dynamic classes, router-link, responsive design

### Phase 3: API Integration and Data Fetching

#### Task 3.1: Create API Services

- [ ] Implement tvmaze.service.ts for API calls
- [ ] Create generic api.service.ts for reusable API functionality
- [ ] Create models for API data
- **Learning Focus**: API integration, TypeScript interfaces, HTTP calls

#### Task 3.2: Create API Composables

- [ ] Implement useApi.ts composable for fetching data
- [ ] Add error handling and loading states
- [ ] Create helper methods for API responses
- **Learning Focus**: Composition API, ref/reactive, error handling

#### Task 3.3: Display Shows on Home Page

- [ ] Implement HomeView.vue with popular shows
- [ ] Create ShowCard.vue component
- [ ] Implement pagination for show listings
- **Learning Focus**: Computed properties, watchers, v-for lists

### Phase 4: Show Details and Episodes

#### Task 4.1: Show Detail Page

- [ ] Implement ShowDetailView.vue
- [ ] Create ShowDetails.vue component
- [ ] Fetch and display show data using route params
- **Learning Focus**: Route params, dynamic component loading, lifecycle hooks

#### Task 4.2: Episode Tracking

- [ ] Implement EpisodeList.vue component
- [ ] Create season tabs and episode lists
- [ ] Add watched/unwatched toggle functionality
- **Learning Focus**: Component communication, event handling, v-model

### Phase 5: State Management with Pinia

#### Task 5.1: Set up Pinia Stores

- [ ] Configure Pinia in the project
- [ ] Create shows.ts store for managing show data
- [ ] Implement actions and getters
- **Learning Focus**: Pinia setup, store structure, actions and getters

#### Task 5.2: User Watchlist

- [ ] Create watchlist.ts store
- [ ] Implement WatchlistButton.vue component
- [ ] Create WatchlistView.vue to display saved shows
- **Learning Focus**: State persistence, complex store interactions

#### Task 5.3: User Preferences

- [ ] Create user.ts store for preferences
- [ ] Implement theme switching functionality
- [ ] Add user settings interface
- **Learning Focus**: Global state, localStorage integration, reactive state

### Phase 6: Advanced Features and Composables

#### Task 6.1: Search Functionality

- [ ] Implement SearchView.vue
- [ ] Create search input with debounce
- [ ] Add filtering options for search results
- **Learning Focus**: Custom directives, debounce patterns, search algorithms

#### Task 6.2: Episode Tracking Composable

- [ ] Create useEpisodeTracking.ts composable
- [ ] Implement watch status tracking functionality
- [ ] Add progress calculation methods
- **Learning Focus**: Complex composables, reusable logic, computed

#### Task 6.3: Local Storage Service

- [ ] Implement storage.service.ts
- [ ] Create data persistence patterns
- [ ] Add migration strategies for data format changes
- **Learning Focus**: Browser storage, data persistence, service patterns

### Phase 7: Dashboard and Statistics

#### Task 7.1: Create Dashboard Layout

- [ ] Implement DashboardLayout.vue
- [ ] Create DashboardView.vue
- [ ] Add dashboard-specific navigation
- **Learning Focus**: Advanced layouts, nested routes, layout switching

#### Task 7.2: Statistics Components

- [ ] Implement StatisticsCard.vue
- [ ] Create ViewingProgress.vue with visualizations
- [ ] Build RecentlyWatchedShows.vue component
- **Learning Focus**: Data visualization, complex calculations, chart libraries

#### Task 7.3: Dashboard Customization

- [ ] Add drag-and-drop for dashboard widgets
- [ ] Implement widget settings
- [ ] Create dashboard persistence
- **Learning Focus**: Third-party libraries, advanced DOM manipulation

### Phase 8: Optimization and Enhancement

#### Task 8.1: Performance Optimization

- [ ] Implement lazy loading for routes and components
- [ ] Add virtual scrolling for long lists
- [ ] Optimize API requests with caching
- **Learning Focus**: Lazy loading, performance patterns, memoization

#### Task 8.2: Offline Support

- [ ] Add service worker configuration
- [ ] Implement offline data access
- [ ] Create offline UI indicators
- **Learning Focus**: PWA concepts, service workers, offline patterns

#### Task 8.3: Final Polish

- [ ] Add animations and transitions
- [ ] Implement error boundaries
- [ ] Create comprehensive form validation
- [ ] Add unit and integration tests
- **Learning Focus**: Transition API, error handling, testing

## Deployment

#### Task 9.1: Build and Deploy

- [ ] Configure production build
- [ ] Set up Netlify deployment
- [ ] Configure CI/CD pipeline
- **Learning Focus**: Build optimization, deployment strategies, environment variables

## Additional Challenge Ideas

- Implement user authentication (Firebase, Auth0, etc.)
- Add social sharing features
- Create a mobile app version with Capacitor or Cordova
- Implement real-time updates with WebSockets
- Add multi-language support with i18n

## Resources

### Vue.js Documentation

- [Vue 3 Guide](https://vuejs.org/guide/introduction.html)
- [Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)
- [TypeScript Support](https://vuejs.org/guide/typescript/overview.html)

### Ecosystem

- [Vue Router](https://router.vuejs.org/)
- [Pinia](https://pinia.vuejs.org/)
- [Vite](https://vitejs.dev/guide/)
- [Tailwind CSS](https://tailwindcss.com/docs)

### API Documentation

- [TVMaze API](https://www.tvmaze.com/api)

## Progress Tracking

Feel free to check the boxes as you complete each task. Add notes about what you learned or challenges you faced to reinforce your learning.

Happy coding! 🚀
