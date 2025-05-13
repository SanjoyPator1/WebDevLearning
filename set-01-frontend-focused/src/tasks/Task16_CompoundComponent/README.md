# Compound Component Pattern: Custom Select Implementation

## Overview

This document explains the compound component pattern and demonstrates it through a custom select component implementation. The compound component pattern is a powerful React pattern that allows for creating flexible, composable UI components with shared internal state.

## Table of Contents

- [What is the Compound Component Pattern?](#what-is-the-compound-component-pattern)
- [Benefits of Compound Components](#benefits-of-compound-components)
- [Custom Select Implementation](#custom-select-implementation)
  - [Component Structure](#component-structure)
  - [React Context Setup](#react-context-setup)
  - [Component Implementation](#component-implementation)
  - [TypeScript Integration](#typescript-integration)
  - [Event Handling](#event-handling)
  - [Outside Click Detection](#outside-click-detection)
- [Usage Examples](#usage-examples)
- [Accessibility Considerations](#accessibility-considerations)
- [Best Practices](#best-practices)
- [Additional Resources](#additional-resources)

## What is the Compound Component Pattern?

The compound component pattern is a design pattern in React where multiple components work together to form a cohesive UI element with shared state and behavior. It's like a family of components that know about each other and coordinate to create a unified experience.

Key characteristics:

- Components share state through React Context
- Components are co-located and designed to work together
- Public API is simplified through composition
- Internal state is managed at the parent level but accessible to children
- Each component has a specific role in the overall functionality

Common examples in popular libraries:

- `<Tabs>`, `<Tab>`, `<TabPanel>` in many UI libraries
- `<Menu>`, `<MenuItem>` in dropdown components
- `<Form>`, `<FormField>`, `<FormInput>` in form libraries

## Benefits of Compound Components

1. **Flexible Composition**: Allows for customized ordering and inclusion of subcomponents.

2. **Intuitive API**: Creates a declarative API that closely resembles the visual hierarchy.

3. **Encapsulated State Management**: Manages complex state internally while still allowing external control.

4. **Reduced Prop Drilling**: Eliminates the need to pass props through multiple levels.

5. **Separation of Concerns**: Each component has a specific, focused role.

6. **Progressive Disclosure**: Simple use cases are easy, complex use cases are possible.

7. **Self-Documenting**: The component usage makes the relationship between parts clear.

## Custom Select Implementation

### Component Structure

Our custom select implementation consists of four main components:

1. **Select**: The main container component that:

   - Manages internal state (open/closed)
   - Provides context to children
   - Handles outside click detection
   - Connects to parent components via value/onChange

2. **Select.Trigger**: The button component that:

   - Toggles the dropdown visibility
   - Displays the current selection or placeholder
   - Shows visual indicators (arrows)

3. **Select.Dropdown**: The container for options that:

   - Renders the list of options
   - Positions itself relative to the trigger
   - Appears/disappears based on state

4. **Select.Option**: The individual option component that:
   - Handles selection events
   - Shows visual indicators for the selected state
   - Renders option content

### React Context Setup

The components communicate via React Context:

```typescript
// Define context type
type SelectContextType = {
  isOpen: boolean;
  selectedValue: string | null;
  toggleDropdown: () => void;
  closeDropdown: () => void;
  handleSelect: (value: string) => void;
};

// Create context
const SelectContext = createContext<SelectContextType | undefined>(undefined);

// Custom hook for consuming context
const useSelectContext = () => {
  const context = useContext(SelectContext);
  if (!context) {
    throw new Error(
      "Select compound components must be used within a Select component"
    );
  }
  return context;
};
```

### Component Implementation

Here's an overview of the key component implementations:

#### Main Select Component

```typescript
const Select = ({
  children,
  onChange,
  value,
  className,
  disabled,
}: SelectProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef<HTMLDivElement>(null);

  // Toggle dropdown state
  const toggleDropdown = useCallback(() => {
    if (!disabled) {
      setIsOpen((prev) => !prev);
    }
  }, [disabled]);

  const closeDropdown = useCallback(() => setIsOpen(false), []);

  const handleSelect = useCallback(
    (optionValue: string) => {
      onChange(optionValue);
      closeDropdown();
    },
    [onChange, closeDropdown]
  );

  // Context value to share with children
  const contextValue: SelectContextType = {
    isOpen,
    toggleDropdown,
    closeDropdown,
    handleSelect,
    selectedValue: value,
  };

  return (
    <SelectContext.Provider value={contextValue}>
      <div
        ref={selectRef}
        className={`relative w-full ${
          disabled ? "opacity-60 cursor-not-allowed" : ""
        } ${className}`}
      >
        {children}
      </div>
    </SelectContext.Provider>
  );
};
```

#### Trigger Component

```typescript
const Trigger = ({ children, className }: TriggerProps) => {
  const { toggleDropdown, isOpen } = useSelectContext();

  return (
    <button
      onClick={toggleDropdown}
      className={`w-full flex items-center justify-between border border-gray-300 btn
      ${isOpen ? "ring-2 ring-blue-500 border-blue-500" : ""} ${className}`}
      aria-haspopup="listbox"
      aria-expanded={isOpen}
    >
      {children}
      {isOpen ? <ArrowUp /> : <ArrowDown />}
    </button>
  );
};
```

#### Dropdown Component

```typescript
const Dropdown = ({ children, className }: DropdownProps) => {
  const { isOpen } = useSelectContext();

  if (!isOpen) return null;

  return (
    <div
      className={`absolute w-full z-10 mt-1 max-h-60 overflow-y-auto bg-white shadow-lg rounded-md ${className}`}
      role="listbox"
    >
      <ul className="py-1">{children}</ul>
    </div>
  );
};
```

#### Option Component

```typescript
const Option = ({ children, value, className }: OptionProps) => {
  const { handleSelect, selectedValue } = useSelectContext();
  const isSelected = selectedValue === value;

  return (
    <li
      onClick={() => handleSelect(value)}
      className={`flex items-center justify-between cursor-pointer py-2 px-4 text-sm 
      ${
        isSelected
          ? "bg-blue-100 text-blue-900 font-medium"
          : "text-gray-900 hover:bg-gray-100"
      } ${className}`}
      role="option"
      aria-selected={isSelected}
    >
      <div className="flex items-center">
        <span
          className={`block truncate ${
            isSelected ? "font-medium" : "font-normal"
          }`}
        >
          {children}
        </span>
      </div>
      {isSelected && (
        <span>
          <Check className="w-5 h-5" />
        </span>
      )}
    </li>
  );
};
```

#### Component Export

```typescript
Select.Trigger = Trigger;
Select.Dropdown = Dropdown;
Select.Option = Option;

export default Select;
```

### TypeScript Integration

Props types for each component:

```typescript
type SelectProps = {
  value: string | null;
  onChange: (value: string) => void;
  children: React.ReactNode;
  disabled?: boolean;
  className?: string;
};

type OptionProps = {
  value: string;
  children: React.ReactNode;
  className?: string;
};

type TriggerProps = {
  children: React.ReactNode;
  className?: string;
};

type DropdownProps = {
  children: React.ReactNode;
  className?: string;
};
```

### Event Handling

The component uses `useCallback` for event handlers to prevent unnecessary re-renders:

```typescript
// Toggle dropdown state
const toggleDropdown = useCallback(() => {
  if (!disabled) {
    setIsOpen((prev) => !prev);
  }
}, [disabled]);

const closeDropdown = useCallback(() => setIsOpen(false), []);

const handleSelect = useCallback(
  (optionValue: string) => {
    onChange(optionValue);
    closeDropdown();
  },
  [onChange, closeDropdown]
);
```

### Outside Click Detection

A critical requirement is detecting clicks outside the component to close the dropdown:

```typescript
// Handle outside click
useEffect(() => {
  const handleClickOutside = (event: MouseEvent) => {
    if (isOpen) {
      if (
        selectRef.current &&
        !selectRef.current.contains(event.target as Node)
      ) {
        closeDropdown();
      }
    }
  };

  if (isOpen) {
    document.addEventListener("mousedown", handleClickOutside);
  }

  // cleanup event listener
  return () => {
    document.removeEventListener("mousedown", handleClickOutside);
  };
}, [isOpen, closeDropdown]);
```

## Usage Examples

Basic usage:

```jsx
function Example() {
  const [selectedValue, setSelectedValue] = (useState < string) | (null > null);

  const handleChange = (value: string) => {
    setSelectedValue(value);
  };

  return (
    <Select value={selectedValue} onChange={handleChange}>
      <Select.Trigger>
        {selectedValue ? `Selected: ${selectedValue}` : "Select an option"}
      </Select.Trigger>
      <Select.Dropdown>
        <Select.Option value="apple">Apple</Select.Option>
        <Select.Option value="mango">Mango</Select.Option>
        <Select.Option value="banana">Banana</Select.Option>
        <Select.Option value="strawberry">Strawberry</Select.Option>
      </Select.Dropdown>
    </Select>
  );
}
```

With custom styling:

```jsx
<Select value={selectedValue} onChange={handleChange} className="w-64 my-4">
  <Select.Trigger className="bg-gray-50 hover:bg-gray-100 p-3">
    {selectedValue ? `Selected: ${selectedValue}` : "Select an option"}
  </Select.Trigger>
  <Select.Dropdown className="bg-white border border-gray-200">
    <Select.Option value="apple" className="hover:bg-blue-50">
      Apple
    </Select.Option>
    <Select.Option value="mango" className="hover:bg-blue-50">
      Mango
    </Select.Option>
  </Select.Dropdown>
</Select>
```

Disabled state:

```jsx
<Select value={selectedValue} onChange={handleChange} disabled={true}>
  <Select.Trigger>Select an option (disabled)</Select.Trigger>
  <Select.Dropdown>
    <Select.Option value="apple">Apple</Select.Option>
    <Select.Option value="mango">Mango</Select.Option>
  </Select.Dropdown>
</Select>
```

## Accessibility Considerations

The implementation includes several accessibility features:

1. **ARIA Attributes**:

   - `aria-haspopup="listbox"` on the trigger
   - `aria-expanded={isOpen}` for screen readers
   - `role="listbox"` on the dropdown
   - `role="option"` on each option
   - `aria-selected={isSelected}` to indicate selection

2. **Keyboard Navigation**:

   - Trigger is a button element for keyboard accessibility
   - Visual focus states

3. **Visual Indicators**:
   - Selected state is visually distinguishable
   - Open/closed state is indicated with arrow direction
   - Checkmark icon for selected option

## Best Practices

1. **Controlled Component Pattern**:

   - Value and onChange props allow parent to control the state
   - Internal state manages only UI aspects (open/closed)

2. **Performance Optimizations**:

   - useCallback for event handlers
   - Conditional rendering for dropdown
   - Event listeners added only when needed

3. **Error Handling**:

   - Context consumer checks if used within provider
   - Provides helpful error messages

4. **Separation of Concerns**:

   - Each component has a specific role
   - Clean composition of subcomponents

5. **Customization**:
   - className props for styling customization
   - Children props for content customization

## Additional Resources

To learn more about compound components:

1. Kent C. Dodds - [Advanced React Patterns](https://kentcdodds.com/blog/compound-components-with-react-hooks)
2. React Patterns - [Compound Components](https://reactpatterns.com/#compound-components)
3. Ryan Florence - [Compound Components Talk](https://www.youtube.com/watch?v=hEGg-3pIHlE)
4. Smashing Magazine - [Compound Components In React](https://www.smashingmagazine.com/2021/08/compound-components-react/)
