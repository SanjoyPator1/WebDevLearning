# React Practice Tasks by Topic

This collection is organized according to Brian Holt's React v9 course structure, with tasks targeting each specific topic. These tasks will help you practice the exact concepts you'll need for an interview.

## COMPLETE INTRO TO REACT

## 1. No Frills React

### Task 1: React Without a Build Step

- Create a simple React application without using any build tools
- Use CDN links to include React and ReactDOM
- Create a component that displays your name and a brief bio
- **Concepts**: React without build tools, CDN imports

### Task 2: Basic Components

- Create a "Hello World" component with props
- Create a Profile Card component that accepts name, title, and description props
- Render multiple instances of your components with different props
- **Concepts**: Components, props, composition

## 2. Core React Concepts

### Task 3: JSX Practice

- Create a component that conditionally renders different UI elements based on a prop
- Use JSX expressions to calculate and display values
- Create a component that renders a list using map()
- Add inline styles and conditional class names
- **Concepts**: JSX syntax, expressions, conditional rendering

### Task 4: useState Hook

- Create a counter component with increment/decrement buttons
- Create a toggle component that switches between two states
- Create a form field that updates state as user types
- Create a component with multiple state variables
- **Concepts**: useState, state updates, event handlers

### Task 5: useEffect Hook

- Create a component that runs different effects:
  - One that runs only on mount
  - One that runs on specific state changes
  - One that runs on every render
  - One with a cleanup function
- Create a component that fetches mock data on mount
- **Concepts**: useEffect dependencies, cleanup, lifecycle simulation

### Task 6: React DevTools

- Create a component with nested state
- Use React DevTools to:
  - Inspect component props and state
  - Modify state values
  - Profile component renders
- Document your findings as comments
- **Concepts**: Debugging, performance monitoring

### Task 7: Custom Hooks

- Create a useLocalStorage hook that persists state to localStorage
- Create a useDocumentTitle hook that updates document title
- Create a useDebounce hook for input fields
- Create a component that uses all three hooks together
- **Concepts**: Custom hooks, hook composition, reusability

### Task 8: Form Input Handling

- Create a form with various input types (text, checkbox, radio, select)
- Handle form submission and prevent default behavior
- Validate inputs and show error messages
- Create controlled inputs with React state
- **Concepts**: Form events, controlled components, input validation

### Task 9: Context API

- Create a theme context provider with light/dark themes
- Create multiple components that consume the theme context
- Add a toggle button to switch themes
- Create a separate context for user preferences
- **Concepts**: Context creation, useContext, provider pattern, multiple contexts

## 3. React Ecosystem

### Task 10: TanStack Router Basics

- Create a simple app with multiple pages using TanStack Router
- Add navigation links between pages
- Create a layout that wraps around all routes
- Add a 404 page for unmatched routes
- **Concepts**: Routing, navigation, layouts, error pages

### Task 11: TanStack Query

- Create a component that uses TanStack Query to fetch mock data
- Implement loading and error states
- Add a refetch button
- Implement a query with parameters that change
- **Concepts**: Data fetching, caching, loading states, refetching

## 4. Advanced React

### Task 12: Portals

- Create a modal component using React Portal
- Make the modal appear/disappear with a button
- Add backdrop that closes modal when clicked
- Ensure modal is accessible and can be closed with ESC key
- **Concepts**: Portals, DOM manipulation, focus management

### Task 13: Error Boundaries

- Create an error boundary component
- Create child components that intentionally throw errors
- Display appropriate fallback UI
- Add a "try again" button to reset the error boundary
- **Concepts**: Error handling, component recovery, fallback UI

### Task 14: Uncontrolled Forms

- Create a form using uncontrolled components with refs
- Handle form submission and collect all values
- Add validation on submission
- Compare with a controlled form implementation
- **Concepts**: Refs, uncontrolled components, form submission

## 5. Testing

### Task 15: Vitest Setup

- Set up Vitest in a React project
- Write a simple test for a component
- Run tests and interpret results
- Configure test environment
- **Concepts**: Test setup, test runners, configuration

### Task 16: Basic Component Tests

- Write tests for a stateless component
- Test that props are rendered correctly
- Test default prop values
- Test component appearance
- **Concepts**: Component testing, assertions, rendering

### Task 17: User Interaction Tests

- Create tests for components with user interactions
- Test button clicks, form submissions, etc.
- Simulate user input in form fields
- Test component state changes after interactions
- **Concepts**: Event simulation, state testing, user flows

### Task 18: Custom Hook Tests

- Write tests for your custom hooks
- Create a test component that uses the hook
- Test hook behavior and return values
- Test hook with different parameters
- **Concepts**: Hook testing, component fixtures, testing state changes

### Task 19: Snapshot Testing

- Create snapshot tests for components
- Update components and see snapshot differences
- Update snapshots when changes are expected
- Test components with different prop combinations
- **Concepts**: Snapshot comparison, visual regression, UI consistency

## INTERMEDIATE REACT

## 6. React Render Modes

### Task 20: Understanding Render Modes

- Create a component that demonstrates different render behavior in:
  - Legacy mode (ReactDOM.render)
  - Concurrent mode (createRoot)
- Add console logs to track render sequence
- Implement components that benefit from concurrent rendering
- **Concepts**: Render modes, concurrent features, rendering behavior

### Task 21: Strict Mode Testing

- Create components with side effects
- Wrap them in StrictMode
- Fix components to handle double-invocation of effects
- Document changes needed for strict mode compliance
- **Concepts**: StrictMode, effect cleanup, development behaviors

## 7. React Server Components

### Task 22: Client vs Server Components

- Create two versions of a component:
  - One as a client component
  - One as a server component
- Document key differences in implementation
- Practice the "use client" directive
- **Concepts**: RSC, component directives, server/client division

### Task 23: Data Fetching Patterns

- Create a component that simulates server-side data fetching
- Implement client-side data fetching with suspense
- Compare the approaches with code comments
- **Concepts**: Data fetching, suspense, loading states

### Task 24: Component Serialization

- Create components that demonstrate what can and cannot be passed between server and client components
- Test passing functions, dates, complex objects
- Implement workarounds for non-serializable data
- **Concepts**: Serialization, props passing, server/client boundaries

## 8. RSCs with Next.js

### Task 25: Next.js App Router

- Create a simple Next.js app with the App Router
- Implement layouts, loading states, and error components
- Create both server and client components
- Implement dynamic routes
- **Concepts**: App router, file-based routing, layouts

### Task 26: Static vs Dynamic Rendering

- Create pages that use:
  - Static rendering
  - Dynamic rendering
  - Streaming rendering
- Document the differences and use cases
- **Concepts**: Rendering strategies, static optimization, streaming

### Task 27: Server Actions

- Create a form that uses server actions
- Implement optimistic updates
- Handle validation and errors
- Compare with client-side form handling
- **Concepts**: Server actions, forms, mutations

## 9. Performance Optimizations

### Task 28: Memoization

- Create a component with expensive calculations
- Implement useMemo to optimize
- Create a component with frequent re-renders
- Use React.memo to prevent unnecessary renders
- **Concepts**: useMemo, React.memo, performance optimization

### Task 29: Callback Optimization

- Create a parent and multiple child components
- Use useCallback to optimize event handlers
- Demonstrate render performance with and without optimization
- **Concepts**: useCallback, function references, render optimization

### Task 30: Code Splitting

- Create an application with multiple large components
- Implement React.lazy and Suspense
- Add prefetching for better UX
- Measure bundle size improvements
- **Concepts**: Code splitting, lazy loading, bundle optimization

## 10. Transitions

### Task 31: useTransition Hook

- Create a component with a search input that filters a large list
- Implement useTransition to keep UI responsive
- Add visual indicators for pending state
- Compare with and without transitions
- **Concepts**: useTransition, concurrency, UI responsiveness

### Task 32: startTransition API

- Create a component that updates multiple pieces of state at once
- Use startTransition to prioritize updates
- Implement pending indicators
- **Concepts**: startTransition, update prioritization, concurrent rendering

## 11. Optimistic Values

### Task 33: Optimistic UI Updates

- Create a component that simulates sending data to a server
- Implement optimistic updates to show changes immediately
- Handle success and error cases
- Roll back changes if the operation fails
- **Concepts**: Optimistic UI, error handling, user experience

### Task 34: useOptimistic Hook (React 19)

- Implement the useOptimistic hook (or simulate its behavior)
- Create a form with optimistic updates
- Handle error states and rollbacks
- **Concepts**: useOptimistic, form submission, state management

## 12. Deferred Values

### Task 35: useDeferredValue Hook

- Create a component with a text input that performs expensive operations
- Use useDeferredValue to defer updating the expensive part
- Add visual feedback for deferred updates
- Compare performance with and without deferring
- **Concepts**: useDeferredValue, performance, user experience

### Task 36: Deferred vs Transition

- Create two components with similar functionality
- Implement one using useDeferredValue
- Implement one using useTransition
- Document differences in behavior and use cases
- **Concepts**: Concurrency patterns, API differences, implementation choice

## 13. Additional Important Topics

### Task 37: Refs and forwardRef

- Create a component that uses useRef to access DOM elements
- Create a component using forwardRef
- Implement imperative handle with useImperativeHandle
- Create a component that measures its size using refs
- **Concepts**: useRef, forwardRef, useImperativeHandle, DOM access

### Task 38: React 19 Features

- Create components that use the `use` hook for promise consumption
- Implement suspense boundaries for loading states
- Create a component using the new React 19 hooks
- **Concepts**: use hook, suspense, React 19 features

### Task 39: State Management Patterns

- Implement multiple state management approaches:
  - useState and prop drilling
  - Context API
  - useReducer
  - External libraries (optional)
- Compare them with a similar example app
- **Concepts**: State management, data flow, state centralization

### Task 40: React Compiler Optimization

- Create components that would benefit from React Compiler optimizations
- Document areas where automatic memoization would help
- Implement manual optimizations that the compiler might perform
- **Concepts**: Compiler optimizations, memoization patterns, render efficiency

### Task 41: Accessibility Implementation

- Create fully accessible components:
  - Modal dialog
  - Dropdown menu
  - Form elements
  - Tabs interface
- Test with keyboard navigation and screen readers
- **Concepts**: a11y, ARIA attributes, keyboard navigation, focus management

### Task 42: CSS-in-JS Approaches

- Implement styling using different approaches:
  - CSS Modules
  - Styled Components or Emotion
  - Tailwind CSS
  - Vanilla CSS
- Compare approaches in a similar component
- **Concepts**: Styling methodologies, CSS-in-JS, component styling

### Task 43: Animation Techniques

- Create animations using:
  - CSS transitions/animations
  - React Transition Group
  - Framer Motion (optional)
- Implement page transitions, element animations, and micro-interactions
- **Concepts**: Animation, transitions, motion libraries

### Task 44: TypeScript in React

- Create strongly-typed components with TypeScript
- Define interfaces for props and state
- Implement generic components
- Use utility types for common patterns
- **Concepts**: TypeScript, type safety, generics, utility types

### Task 45: Deployment and Optimization

- Setup a build pipeline for a React application
- Optimize bundle size
- Implement preloading and prefetching
- Configure CI/CD for deployment
- **Concepts**: Builds, optimization, deployment, CI/CD

## Implementation Tips

For all tasks, keep these guidelines in mind:

1. **Focus on Concepts**: The goal is to understand and practice the specific React concepts, not to create full applications.
2. **Use Mock Data**: Create constants or simple generators for mock data instead of APIs.
3. **Document Learning**: Add comments explaining key concepts and why you implemented things a certain way.
4. **Compare Approaches**: When appropriate, implement multiple solutions to compare different approaches.
5. **Test Edge Cases**: Consider how your components handle empty states, errors, and unexpected inputs.
6. **Measure Performance**: For optimization tasks, measure and document performance improvements.
7. **Incremental Practice**: Start with the basics and gradually progress to more advanced topics.

Good luck with your interview preparation! These tasks cover all the major topics from Brian Holt's course and should give you excellent practice for your React interview.
