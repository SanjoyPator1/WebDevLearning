# Task 1.2: Create Base UI Components

This guide will walk you through creating the base UI components for your ShowTrackr application. These components will serve as the building blocks for your application's interface, promoting reusability and consistent design.

## Learning Objectives

By completing this task, you will learn about:

1. **Vue Component Basics**: How to structure and create Vue components
2. **Props**: Passing data into components
3. **Slots**: Content distribution in components
4. **Events**: Component communication through custom events
5. **Conditional Rendering**: Showing/hiding elements based on conditions

## Components to Create

You'll be creating three foundational UI components:

1. **BaseButton.vue**: A reusable button component
2. **BaseCard.vue**: A container component with slots
3. **BaseLoader.vue**: A loading indicator component

Let's dive into each component in detail.

## 1. BaseButton.vue

### Concepts to Apply

- **Props**: Customize button appearance and behavior
- **Events**: Emit click events to parent components
- **Slots**: Allow custom content inside the button
- **Conditional Classes**: Apply different styles based on props

### Implementation Steps

1. Create a new file at `src/components/ui/BaseButton.vue`
2. Implement the component with the following features:
   - Button variants (primary, secondary, etc.)
   - Size options (small, medium, large)
   - Disabled state
   - Loading state
   - Icon support

### Example Implementation

```vue
<template>
  <button
    :class="[
      'btn',
      `btn-${variant}`,
      `btn-${size}`,
      { 'opacity-50 cursor-not-allowed': disabled, 'flex items-center': hasIcon },
    ]"
    :disabled="disabled || loading"
    @click="onClick"
    :type="type"
  >
    <span v-if="loading" class="mr-2">
      <!-- You can add a small spinner icon here -->
      <span
        class="animate-spin inline-block h-4 w-4 border-2 border-t-transparent border-white rounded-full"
      ></span>
    </span>
    <!-- This allows us to pass any content inside the button -->
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// Define props with TypeScript
interface Props {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  type?: 'button' | 'submit' | 'reset'
}

// Define props with default values
const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
  loading: false,
  type: 'button',
})

// Define emits
const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>()

// Computed property to check if button has icon
const hasIcon = computed(() => !!slots.icon)

// Define click handler that emits the click event
const onClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<style scoped>
.btn {
  @apply font-medium rounded-lg px-4 py-2 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2;
}

.btn-primary {
  @apply bg-primary text-white hover:bg-primary-dark focus:ring-primary-light;
}

.btn-secondary {
  @apply bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-300;
}

.btn-danger {
  @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
}

.btn-success {
  @apply bg-green-600 text-white hover:bg-green-700 focus:ring-green-500;
}

.btn-outline {
  @apply border border-primary text-primary hover:bg-primary hover:text-white focus:ring-primary-light;
}

.btn-sm {
  @apply text-sm px-3 py-1;
}

.btn-md {
  @apply text-base px-4 py-2;
}

.btn-lg {
  @apply text-lg px-6 py-3;
}
</style>
```

## 2. BaseCard.vue

### Concepts to Apply

- **Slots**: Default slot for main content and named slots for header and footer
- **Props**: Allow customization of card appearance
- **Styling Options**: Provide different styling options through props

### Implementation Steps

1. Create a new file at `src/components/ui/BaseCard.vue`
2. Implement a component with:
   - Main content slot
   - Optional header and footer slots
   - Styling customizations (padding, shadow, rounded corners)

### Example Implementation

```vue
<template>
  <div
    :class="[
      'bg-white dark:bg-gray-800',
      'border border-gray-200 dark:border-gray-700',
      shadow ? `shadow-${shadow}` : '',
      rounded ? `rounded-${rounded}` : 'rounded-lg',
      { 'overflow-hidden': overflow },
    ]"
  >
    <!-- Header slot with conditional rendering -->
    <div
      v-if="$slots.header"
      :class="['px-6 py-4 border-b border-gray-200 dark:border-gray-700', headerClass]"
    >
      <slot name="header"></slot>
    </div>

    <!-- Main content with configurable padding -->
    <div :class="[padding ? `p-${padding}` : 'p-6', bodyClass]">
      <slot></slot>
    </div>

    <!-- Footer slot with conditional rendering -->
    <div
      v-if="$slots.footer"
      :class="['px-6 py-4 border-t border-gray-200 dark:border-gray-700', footerClass]"
    >
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  shadow?: 'sm' | 'md' | 'lg' | 'xl' | 'none'
  rounded?: 'sm' | 'md' | 'lg' | 'xl' | 'none'
  padding?: 'none' | '2' | '4' | '6' | '8'
  overflow?: boolean
  headerClass?: string
  bodyClass?: string
  footerClass?: string
}

// Define props with default values
withDefaults(defineProps<Props>(), {
  shadow: 'md',
  rounded: 'lg',
  padding: '6',
  overflow: true,
  headerClass: '',
  bodyClass: '',
  footerClass: '',
})
</script>
```

## 3. BaseLoader.vue

### Concepts to Apply

- **Conditional Rendering**: Show/hide based on loading state
- **Props**: Configure loader appearance and behavior
- **Animation**: Use CSS animations for loading effects

### Implementation Steps

1. Create a new file at `src/components/ui/BaseLoader.vue`
2. Implement a component that:
   - Can be shown/hidden based on loading state
   - Has size variations
   - Has multiple visual styles

### Example Implementation

```vue
<template>
  <div
    v-if="show"
    :class="[
      'flex items-center justify-center',
      fullScreen ? 'fixed inset-0 bg-black bg-opacity-50 z-50' : '',
      overlay && !fullScreen
        ? 'absolute inset-0 bg-white bg-opacity-75 dark:bg-gray-900 dark:bg-opacity-75'
        : '',
      centered && !fullScreen ? 'absolute inset-0' : '',
      wrapperClass,
    ]"
  >
    <!-- Spinner loader -->
    <div v-if="type === 'spinner'" :class="['animate-spin', sizeClasses]">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        :class="['text-primary dark:text-primary-light', sizeClasses]"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        ></circle>
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
    </div>

    <!-- Pulse loader -->
    <div v-else-if="type === 'pulse'" :class="['flex space-x-2', sizeClasses]">
      <div class="bg-primary rounded-full animate-pulse" :style="dotStyle"></div>
      <div class="bg-primary rounded-full animate-pulse delay-75" :style="dotStyle"></div>
      <div class="bg-primary rounded-full animate-pulse delay-150" :style="dotStyle"></div>
    </div>

    <!-- Text loader with slot -->
    <div v-if="$slots.default" class="mt-4 text-center text-gray-600 dark:text-gray-300">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  show?: boolean
  size?: 'sm' | 'md' | 'lg'
  type?: 'spinner' | 'pulse'
  fullScreen?: boolean
  overlay?: boolean
  centered?: boolean
  wrapperClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  show: true,
  size: 'md',
  type: 'spinner',
  fullScreen: false,
  overlay: false,
  centered: true,
  wrapperClass: '',
})

// Compute size-based classes
const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'w-4 h-4'
    case 'lg':
      return 'w-12 h-12'
    case 'md':
    default:
      return 'w-8 h-8'
  }
})

// Compute dot style for pulse loader
const dotStyle = computed(() => {
  let size
  switch (props.size) {
    case 'sm':
      size = '0.5rem'
      break
    case 'lg':
      size = '1rem'
      break
    case 'md':
    default:
      size = '0.75rem'
      break
  }

  return {
    width: size,
    height: size,
  }
})
</script>

<style scoped>
.delay-75 {
  animation-delay: 0.25s;
}

.delay-150 {
  animation-delay: 0.5s;
}
</style>
```

## Testing Your Components

After creating these components, you can test them in a new test page or within your existing pages. Create a simple test component:

```vue
<template>
  <div class="space-y-8 p-8">
    <section>
      <h2 class="text-2xl font-bold mb-4">Button Examples</h2>
      <div class="space-x-2 space-y-2">
        <BaseButton>Default Button</BaseButton>
        <BaseButton variant="secondary">Secondary</BaseButton>
        <BaseButton variant="danger">Danger</BaseButton>
        <BaseButton variant="success">Success</BaseButton>
        <BaseButton variant="outline">Outline</BaseButton>
        <BaseButton disabled>Disabled</BaseButton>
        <BaseButton loading>Loading</BaseButton>
        <BaseButton size="sm">Small</BaseButton>
        <BaseButton size="lg">Large</BaseButton>
      </div>
    </section>

    <section>
      <h2 class="text-2xl font-bold mb-4">Card Examples</h2>
      <div class="space-y-4">
        <BaseCard>
          <p>This is a basic card with default styling.</p>
        </BaseCard>

        <BaseCard>
          <template #header>
            <h3 class="text-xl font-semibold">Card with Header</h3>
          </template>
          <p>This card has a header and default content.</p>
        </BaseCard>

        <BaseCard>
          <template #header>
            <h3 class="text-xl font-semibold">Complete Card</h3>
          </template>
          <p>This card has a header, content, and footer.</p>
          <template #footer>
            <div class="flex justify-end">
              <BaseButton size="sm">Action</BaseButton>
            </div>
          </template>
        </BaseCard>

        <BaseCard shadow="xl" rounded="xl" padding="8">
          <p>Card with custom styling (extra shadow, rounded corners, and padding).</p>
        </BaseCard>
      </div>
    </section>

    <section>
      <h2 class="text-2xl font-bold mb-4">Loader Examples</h2>
      <div class="space-y-4">
        <div class="relative h-20 border border-gray-200 rounded-lg">
          <BaseLoader />
        </div>

        <div class="relative h-20 border border-gray-200 rounded-lg">
          <BaseLoader type="pulse" />
        </div>

        <div class="relative h-20 border border-gray-200 rounded-lg">
          <BaseLoader size="sm">Loading small...</BaseLoader>
        </div>

        <div class="relative h-20 border border-gray-200 rounded-lg">
          <BaseLoader size="lg" overlay>Loading with overlay...</BaseLoader>
        </div>

        <BaseButton @click="toggleFullScreenLoader">Show Full Screen Loader</BaseButton>
        <BaseLoader v-if="showFullScreenLoader" fullScreen> Loading full screen... </BaseLoader>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseLoader from '@/components/ui/BaseLoader.vue'

const showFullScreenLoader = ref(false)

const toggleFullScreenLoader = () => {
  showFullScreenLoader.value = true
  setTimeout(() => {
    showFullScreenLoader.value = false
  }, 2000)
}
</script>
```

## Key Vue.js Concepts Explained

### 1. Props

Props are custom attributes you can register on a component. When a value is passed to a prop attribute, it becomes a property on that component instance. Props allow you to pass data from a parent component to a child component.

**Example from BaseButton.vue:**

```typescript
interface Props {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  type?: 'button' | 'submit' | 'reset';
}

// Usage in parent component:
<BaseButton variant="primary" size="lg" :disabled="false">
  Click Me
</BaseButton>
```

### 2. Slots

Slots are Vue's content distribution API that allows you to inject content from the parent component into specific locations of the child component.

**Types of slots:**

- **Default slot**: Content without a `name` attribute goes into the default slot
- **Named slots**: Designated areas for specific content using the `name` attribute

**Example from BaseCard.vue:**

```vue
<!-- In BaseCard.vue -->
<div v-if="$slots.header" class="card-header">
  <slot name="header"></slot>
</div>
<div class="card-content">
  <slot></slot> <!-- Default slot -->
</div>
<div v-if="$slots.footer" class="card-footer">
  <slot name="footer"></slot>
</div>

<!-- Usage in parent component -->
<BaseCard>
  <template #header>Card Title</template>
  <p>This is the main content.</p>
  <template #footer>Card Footer</template>
</BaseCard>
```

### 3. Events

Vue components can emit custom events that parent components can listen for. This is a primary method of communication from child to parent.

**Example from BaseButton.vue:**

```typescript
// Define emits
const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void;
}>();

// Emit the event
const onClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event);
  }
};

// Usage in parent component:
<BaseButton @click="handleButtonClick">Click Me</BaseButton>
```

### 4. Conditional Rendering

Vue allows you to conditionally render elements using `v-if` and `v-show` directives.

**Example from BaseLoader.vue:**

```vue
<!-- Show loader only when 'show' prop is true -->
<div v-if="show" class="loader">
  <!-- Loader content -->
</div>

<!-- Show different loader types based on 'type' prop -->
<div v-if="type === 'spinner'">
  <!-- Spinner loader -->
</div>
<div v-else-if="type === 'pulse'">
  <!-- Pulse loader -->
</div>
```

### 5. Computed Properties

Computed properties are used for complex logic that depends on reactive data. They are cached based on their dependencies and only re-evaluated when their dependencies change.

**Example from BaseLoader.vue:**

```typescript
const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'w-4 h-4'
    case 'lg':
      return 'w-12 h-12'
    case 'md':
    default:
      return 'w-8 h-8'
  }
})
```

## Adding Components to Your Project

To integrate these components in your project:

1. Create a folder structure:

   ```
   src/
   ├── components/
   │   ├── ui/
   │   │   ├── BaseButton.vue
   │   │   ├── BaseCard.vue
   │   │   └── BaseLoader.vue
   ```

2. Create each component file with the implementations provided above

3. Optionally, create an index.ts file in the ui folder to make imports easier:

   ```typescript
   // src/components/ui/index.ts
   export { default as BaseButton } from './BaseButton.vue'
   export { default as BaseCard } from './BaseCard.vue'
   export { default as BaseLoader } from './BaseLoader.vue'
   ```

4. Use the components in your pages and other components by importing them:

   ```vue
   <script setup lang="ts">
   import { BaseButton, BaseCard, BaseLoader } from '@/components/ui'
   </script>

   <template>
     <BaseCard>
       <template #header>Card Title</template>
       <p>Card content goes here</p>
       <template #footer>
         <BaseButton @click="doSomething">Click Me</BaseButton>
       </template>
     </BaseCard>

     <BaseLoader v-if="isLoading" />
   </template>
   ```

## Extending These Components

As your application grows, you might want to extend these components:

- **BaseButton.vue**: Add icon support, different button styles, or button groups
- **BaseCard.vue**: Add collapsible functionality, different color themes, or card actions
- **BaseLoader.vue**: Add more loader types, progress indicators, or skeleton loaders

## Conclusion

By creating these base UI components, you're setting a foundation for consistent design throughout your application. These components promote reusability and make your codebase more maintainable.

In the next phase, you'll create layout components that will use these base UI components to structure your application's pages.

Happy coding!
