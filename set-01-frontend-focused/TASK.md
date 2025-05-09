# React Interview Practice Tasks (Frontend-Focused)

This collection provides focused React practice tasks that don't require a backend. Each task targets specific React concepts you might be tested on during a hands-on interview. All data can be handled with constants, mock data arrays, or localStorage.

## Basic Component Tasks

### Task 1: Counter Component

Create a simple counter with increment and decrement buttons.

- Initial count starts at 0
- Increment and decrement buttons
- Reset button
- Counter cannot go below 0
- **Concepts**: useState, event handling

### Task 2: Toggle Component

Create a button that toggles between ON and OFF states.

- Button text changes based on state
- Background color changes based on state
- **Concepts**: useState, conditional rendering

### Task 3: Text Expander

Create a "Read More/Read Less" component.

- Show truncated text with "Read More" button
- Clicking expands to show full text with "Read Less" button
- Make the character limit configurable via props
- **Concepts**: props, useState, conditional rendering

### Task 4: Accordion Component

Create a simple accordion component.

- Display a list of items with titles
- Clicking a title shows/hides its content
- **Mock data**: Array of {title, content} objects
- **Concepts**: useState, mapping over data, conditional rendering

### Task 5: Tabs Component

Implement a basic tabs interface.

- Display multiple tabs with different content
- Only one tab content visible at a time
- **Mock data**: Array of {tabName, content} objects
- **Concepts**: useState, conditional rendering, component composition

## State Management Tasks

### Task 6: Todo List with useState

Create a todo list using just React's useState.

- Add new todos
- Delete todos
- Mark todos as complete
- **Concepts**: useState with array updates, form handling

### Task 7: Traffic Light

Create a traffic light with three lights (red, yellow, green).

- Only one light active at a time
- Button to cycle through the lights
- Optional: Auto-cycle with a timer
- **Concepts**: useState, useEffect, CSS styling

### Task 8: Form with Multiple Inputs

Create a form with multiple input fields.

- Name, email, password fields
- Show entered data below form
- Reset button to clear form
- **Concepts**: useState with objects, form handling

### Task 9: Parent-Child Communication

Create a parent component with multiple child counter components.

- Parent displays total from all child counters
- Each child can increment/decrement its own value
- Parent has button to reset all counters
- **Concepts**: props, lifting state up, parent-child communication

### Task 10: Shopping Cart with Context

Implement a simple shopping cart using React Context.

- **Mock data**: Array of product objects
- Display products list with "Add to Cart" buttons
- Show cart with added items and total price
- Remove items from cart
- **Concepts**: useContext, useReducer, Context Provider

## Effect and Lifecycle Tasks

### Task 11: Timer/Stopwatch

Create a stopwatch with start, stop, and reset functions.

- Display time in mm:ss format
- Start, stop, and reset buttons
- **Concepts**: useEffect, cleanup function, interval management

### Task 12: Debounced Search

Create a search input with debounced functionality.

- Input field for search term
- Only perform search after user stops typing for 500ms
- **Mock data**: Array of items to search through
- **Concepts**: useEffect, cleanup, debouncing, setTimeout

### Task 13: Window Size Tracker

Create a component that displays the current window dimensions.

- Show width and height of the browser window
- Update when window is resized
- **Concepts**: useEffect, window events, cleanup

### Task 14: Data Fetching Simulation

Simulate data fetching with artificial delay.

- **Mock data**: Array of items
- Add setTimeout to simulate network request
- Show loading state
- Handle success and error states
- **Concepts**: useEffect, async operations, loading states

### Task 15: Custom useFetch Hook

Create a reusable data fetching hook.

- Create a useFetch hook that simulates API calls
- Handle loading, error, and success states
- Accept timeout parameter to control delay
- **Concepts**: custom hooks, useState, useEffect

## Advanced Component Patterns

### Task 16: Compound Component Pattern

Create a custom select component using compound components.

- Main Select component with Select.Option children
- Clicking Select opens dropdown
- Selecting an option updates parent value
- Close dropdown when clicking outside
- **Concepts**: React.Children, context, compounding components

### Task 17: Render Props Pattern

Implement a hover card using render props.

- Create a HoverCard component that accepts render props
- Detect mouse hover over element
- Show additional content on hover
- **Concepts**: render props, useState, mouse events

### Task 18: Higher Order Components

Create a HOC that adds loading functionality.

- Create withLoading HOC
- Wrapped components show spinner while loading
- Pass loading state into wrapped component
- **Concepts**: HOCs, function composition, props passing

### Task 19: Custom Hook with localStorage

Create a hook to persist state in localStorage.

- Implement useLocalStorage hook
- Save and retrieve values from localStorage
- Update localStorage when state changes
- **Concepts**: custom hooks, localStorage, useEffect

### Task 20: Optimized List Rendering

Create a list with optimized rendering.

- **Mock data**: Array of 1000+ list items
- Use React.memo to prevent unnecessary renders
- Implement virtualized list rendering (show only visible items)
- **Concepts**: React.memo, performance optimization, useCallback

## Performance Optimization Tasks

### Task 21: Memoization Practice

Create a component with expensive calculations.

- Input field for a number
- Calculate and display Fibonacci sequence up to that number
- Use useMemo to memoize calculation
- Add unrelated state to demonstrate memoization effectiveness
- **Concepts**: useMemo, performance, expensive calculations

### Task 22: useCallback Implementation

Create parent and child components using useCallback.

- Parent with multiple state variables
- Child that receives callback function
- Use React.memo on child
- Compare with/without useCallback
- **Concepts**: useCallback, React.memo, reference equality

### Task 23: React.lazy and Code Splitting

Implement code splitting with React.lazy.

- Create multiple page components
- Use React.lazy to load them dynamically
- Add Suspense with fallback
- **Concepts**: React.lazy, Suspense, code splitting

### Task 24: Avoiding Unnecessary Renders

Fix a component with unnecessary render problems.

- Parent component with multiple state variables
- Multiple child components that depend on specific props
- Optimize to prevent children re-rendering when unrelated state changes
- **Concepts**: React.memo, optimization, props dependencies

### Task 25: Custom Comparison Function

Create a component using custom comparison in memo.

- Component receives complex prop (array or object)
- Implement custom comparison function for React.memo
- Toggle between default and custom comparison
- **Concepts**: React.memo with custom comparer, deep comparison

## UI Pattern Tasks

### Task 26: Modal Dialog

Create a reusable modal component.

- Button to open modal
- Close button inside modal
- Close on overlay click
- Prevent scroll on body when open
- **Concepts**: portals, useEffect, event listeners

### Task 27: Auto-complete Search

Create an autocomplete component.

- **Mock data**: Array of searchable items
- Input that shows matching results as you type
- Select result to fill input
- Keyboard navigation through results
- **Concepts**: filtering, keyboard events, accessibility

### Task 28: Carousel/Slider

Build an image carousel.

- **Mock data**: Array of image URLs
- Next/previous buttons
- Optional: Auto-slide with pause on hover
- **Concepts**: useState, useEffect, transitions

### Task 29: Drag and Drop Sorting

Create a sortable list with drag and drop.

- **Mock data**: Array of items
- Allow reordering via drag and drop
- Visual feedback during drag
- **Concepts**: mouse events, array manipulation, refs

### Task 30: Infinite Scroll with Mock Data

Implement infinite scrolling.

- **Mock data**: Function that generates chunks of data
- Initial load of items
- Load more when scrolling to bottom
- Loading indicator
- **Concepts**: scroll events, useEffect, state updates

## Form and Validation Tasks

### Task 31: Dynamic Form Fields

Create a form with dynamic field addition/removal.

- Initial form with a few fields
- Button to add new field instances
- Button to remove field instances
- Submit button that collects all data
- **Concepts**: array manipulation, forms, dynamic components

### Task 32: Multi-step Form

Create a multi-step form with validation.

- Form split into multiple steps/pages
- Next/previous navigation
- Validation before proceeding to next step
- Summary page at the end
- **Concepts**: form state management, validation, multi-step UI

### Task 33: Form Validation with Custom Hook

Create a custom form validation hook.

- Implement useForm hook with validation
- Support different validation rules
- Show error messages
- Disable submit until valid
- **Concepts**: custom hooks, validation logic, form handling

### Task 34: Credit Card Input

Create a credit card input form with formatting.

- Format input as user types (add spaces every 4 digits)
- Validate card number using Luhn algorithm
- Show card type based on starting digits
- **Concepts**: input masking, validation, pattern matching

### Task 35: Password Strength Meter

Create a password input with strength indicator.

- Password input field
- Strength meter showing weak/medium/strong
- Requirements list (uppercase, lowercase, number, special char)
- Check off requirements as they're met
- **Concepts**: regex, visual feedback, state management

## Animation and Styling Tasks

### Task 36: Animated Notifications

Create a notifications system with animations.

- Function to add new notifications
- Notifications appear with entrance animation
- Auto-dismiss with exit animation
- Manual dismiss button
- **Concepts**: animation, queuing, timing

### Task 37: Theme Switcher

Create a theme switcher with multiple themes.

- Toggle between at least 3 themes
- Affect colors, borders, shadows, etc.
- Store preference in localStorage
- **Concepts**: CSS variables, themes, localStorage

### Task 38: Animated Accordion

Enhance the accordion from Task 4 with animations.

- Smooth height transitions when opening/closing
- Optional: Rotate arrow indicator
- **Concepts**: CSS transitions, height animation, refs

### Task 39: Loading Skeletons

Create components with loading skeleton states.

- Design card components with content
- Create skeleton versions with animated loading effect
- Toggle between loaded and loading states
- **Concepts**: loading states, CSS animations, conditional rendering

### Task 40: Micro-Interactions

Add micro-interactions to form elements.

- Button with click animations
- Checkbox with toggle animation
- Radio button with selection animation
- Input with focus effects
- **Concepts**: micro-interactions, CSS transitions, user feedback

## Accessibility Tasks

### Task 41: Keyboard Navigation

Create a menu system navigable by keyboard.

- Menu with dropdown submenus
- Keyboard navigation (arrows, enter, escape)
- Proper focus management
- **Concepts**: keyboard events, focus management, accessibility

### Task 42: Screen Reader Friendly Components

Create components with proper ARIA attributes.

- Custom checkbox component
- Error messages that are screen reader accessible
- Status updates that announce to screen readers
- **Concepts**: ARIA attributes, accessibility, semantic HTML

### Task 43: Focus Trap for Modal

Enhance the modal from Task 26 with a focus trap.

- Trap focus inside modal when open
- Cycle through focusable elements
- Close on escape key
- Return focus to trigger when closed
- **Concepts**: focus management, keyboard navigation, accessibility

### Task 44: Color Contrast Checker

Create a component that checks color contrast.

- Input for foreground and background colors
- Display contrast ratio
- Show pass/fail for WCAG standards
- Preview text with selected colors
- **Concepts**: color manipulation, accessibility standards, user input

### Task 45: Accessible Form Errors

Create a form with accessible error handling.

- Form with multiple inputs
- Inline validation
- Errors announced to screen readers
- Visual error indicators
- **Concepts**: form validation, ARIA-live regions, accessibility

## Implementation Notes

For all tasks, keep these guidelines in mind:

1. **Mock Data**: Use constants or arrays directly in your code instead of API calls.
2. **TypeScript**: Use TypeScript for better type safety and props validation.
3. **Components**: Break down your UI into small, reusable components.
4. **Props**: Use proper prop types and provide default props where appropriate.
5. **Comments**: Add comments explaining any complex logic.
6. **Styling**: Keep styling simple using CSS modules, styled-components, or plain CSS.
7. **Error Handling**: Include error states where applicable.
8. **Naming**: Use clear, consistent naming conventions.
9. **State Management**: Choose appropriate state management for each task (local state vs. context vs. prop drilling).

Each task is designed to focus on a specific React concept or pattern that might come up in an interview. Good luck with your preparation!
