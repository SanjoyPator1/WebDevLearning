# Task 1.1: Project Initialization and Configuration

This guide walks through the initial setup of your ShowTrackr Vue.js application, explaining the technologies used and configuration choices made.

## Learning Objectives

By completing this task, you will learn about:

1. **Vue.js 3 Project Setup**: Creating a new Vue project with Vite
2. **TypeScript Integration**: Configuring TypeScript for type safety
3. **Code Quality Tools**: Setting up ESLint and Prettier
4. **CSS Framework**: Integrating Tailwind CSS
5. **Project Structure**: Organizing files and folders effectively

## Step 1: Install and Set Up the Vue.js Project with Vite

### Why Vite?

Vite is a modern build tool that provides an extremely fast development experience:

- **Fast Server Start**: No bundling during development, uses native ES modules
- **Hot Module Replacement (HMR)**: Instant updates in the browser
- **Optimized Build**: Rollup-based bundling for production

### Creating a New Project

To create a new Vue.js project with Vite:

```bash
npm create vite@latest showtrackr -- --template vue-ts
cd showtrackr
npm install
```

This command:

1. Creates a new project called "showtrackr"
2. Uses the Vue + TypeScript template
3. Installs all dependencies

## Step 2: Configure TypeScript

TypeScript provides static type checking to help catch errors during development.

### Understanding the TypeScript Configuration

The `tsconfig.json` file in your project root should look similar to this:

```json
{
  "files": [],
  "references": [
    {
      "path": "./tsconfig.node.json"
    },
    {
      "path": "./tsconfig.app.json"
    },
    {
      "path": "./tsconfig.vitest.json"
    }
  ]
}
```

The `tsconfig.app.json` file contains the main TypeScript configuration:

```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "include": ["env.d.ts", "src/**/*", "src/**/*.vue"],
  "exclude": ["src/**/__tests__/*"],
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Key TypeScript Configuration Options

- **extends**: Inherits settings from Vue's base configuration
- **include**: Specifies which files to include in compilation
- **exclude**: Specifies which files to exclude from compilation
- **compilerOptions.paths**: Configures import path aliases (e.g., `@/components` resolves to `src/components`)
- **compilerOptions.incremental**: Enables incremental builds for faster compilation

## Step 3: Configure ESLint and Prettier

ESLint checks your code for potential errors and enforces coding standards, while Prettier ensures consistent code formatting.

### ESLint Configuration

The ESLint configuration is in `eslint.config.ts`:

```typescript
import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },
  skipFormatting,
)
```

### Prettier Configuration

The Prettier configuration is in `.prettierrc.json`:

```json
{
  "$schema": "https://json.schemastore.org/prettierrc",
  "semi": false,
  "singleQuote": true,
  "printWidth": 100
}
```

This configuration:

- Removes semicolons at the end of statements
- Uses single quotes for strings
- Sets the line length limit to 100 characters

## Step 4: Set Up Tailwind CSS

Tailwind CSS is a utility-first CSS framework that allows for rapid UI development.

### Installing and Configuring Tailwind

1. Install Tailwind CSS and its dependencies:

```bash
npm install -D tailwindcss@latest postcss@latest autoprefixer@latest
npx tailwindcss init
```

2. Configure the Tailwind CSS in `tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {},
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

3. Create a CSS file (e.g., `src/assets/styles/main.css`) to import Tailwind:

```css
@import 'tailwindcss';
```

4. Import the CSS file in your main entry point (`src/main.ts`):

```typescript
import './assets/styles/main.css'
```

## Step 5: Configure Basic Folder Structure

A well-organized folder structure makes your project more maintainable.

### Recommended Folder Structure

```
showtrackr/
├── public/              # Static assets
├── src/
│   ├── assets/          # Images, styles, etc.
│   │   ├── images/
│   │   └── styles/
│   ├── components/      # Vue components
│   │   ├── common/      # Shared components (header, footer)
│   │   ├── dashboard/   # Dashboard-specific components
│   │   ├── icons/       # Icon components
│   │   ├── shows/       # Show-related components
│   │   └── ui/          # Base UI components
│   ├── composables/     # Reusable composition functions
│   ├── layouts/         # Page layouts
│   ├── models/          # TypeScript interfaces
│   ├── router/          # Vue Router configuration
│   ├── services/        # API services
│   ├── stores/          # Pinia stores
│   ├── utils/           # Utility functions
│   │   └── constants/   # Constants used throughout the app
│   ├── views/           # Page components
│   ├── App.vue          # Root component
│   └── main.ts          # Application entry point
└── ...                  # Configuration files
```

### Key Folders Explained

- **components/**: Contains reusable Vue components
  - **common/**: Components used across multiple pages (e.g., headers, footers)
  - **ui/**: Base UI components (buttons, cards, form inputs)
- **composables/**: Reusable composition functions (custom hooks)
- **layouts/**: Page layout components for consistent page structure
- **models/**: TypeScript interfaces for data models
- **services/**: API service functions
- **stores/**: Pinia state management stores
- **views/**: Page components that represent routes

## Additional Configuration Files

### Vite Configuration

The `vite.config.ts` file configures the Vite build tool:

```typescript
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), vueDevTools(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
```

### Vue Router Configuration

The `src/router/index.ts` file configures routing:

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
    // Other routes...
  ],
})

export default router
```

## Key Learning Points

1. **Modern Frontend Development**: Using Vue.js 3 with Vite for a fast development experience
2. **Type Safety**: TypeScript integration to catch errors early
3. **Code Quality**: ESLint and Prettier for consistent, high-quality code
4. **Utility-First CSS**: Tailwind CSS for rapid UI development
5. **Project Organization**: Structured folders for better maintainability

## Next Steps

After completing this task, you should have a well-configured Vue.js project with TypeScript, ESLint, Prettier, and Tailwind CSS. The project structure is set up to support future development efficiently.

Move on to Task 1.2 to create base UI components that will serve as the building blocks for your application's interface.
