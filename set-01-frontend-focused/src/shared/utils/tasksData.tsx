import type { AccordionItemType } from "../../tasks/Task04_Accordion/Accordion";
import type { TabItemType } from "../../tasks/Task05_Tabs/Tabs";

export interface TaskData {
  id: string;
  name: string;
  completed: boolean;
}

export interface TaskCategory {
  name: string;
  tasks: TaskData[];
}

// List of all available tasks
const tasks: TaskData[] = [
  // Basic Components
  { id: "counter", name: "Task 1: Counter", completed: true },
  { id: "toggle", name: "Task 2: Toggle", completed: true },
  { id: "textExpander", name: "Task 3: Text Expander", completed: true },
  { id: "accordion", name: "Task 4: Accordion", completed: true },
  { id: "tabs", name: "Task 5: Tabs", completed: true },

  // State Management
  { id: "todoList", name: "Task 6: Todo List", completed: false },
  { id: "trafficLight", name: "Task 7: Traffic Light", completed: false },
  { id: "formInputs", name: "Task 8: Form Inputs", completed: false },
  { id: "parentChild", name: "Task 9: Parent-Child", completed: false },
  {
    id: "shoppingCart",
    name: "Task 10: Shopping Cart with Context",
    completed: false,
  },

  // Effects & Lifecycle
  { id: "timer", name: "Task 11: Timer/Stopwatch", completed: false },
  {
    id: "debouncedSearch",
    name: "Task 12: Debounced Search",
    completed: false,
  },
  {
    id: "windowSizeTracker",
    name: "Task 13: Window Size Tracker",
    completed: false,
  },
  { id: "dataFetching", name: "Task 14: Data Fetching", completed: false },
  {
    id: "customFetchHook",
    name: "Task 15: Custom useFetch Hook",
    completed: false,
  },

  // Advanced Component Patterns
  {
    id: "compoundComponent",
    name: "Task 16: Compound Component",
    completed: false,
  },
  { id: "renderProps", name: "Task 17: Render Props", completed: false },
  { id: "hoc", name: "Task 18: Higher Order Components", completed: false },
  {
    id: "localStorageHook",
    name: "Task 19: LocalStorage Hook",
    completed: false,
  },
  { id: "optimizedList", name: "Task 20: Optimized List", completed: false },

  // Performance Optimization
  { id: "memoization", name: "Task 21: Memoization", completed: false },
  { id: "useCallback", name: "Task 22: useCallback", completed: false },
  { id: "lazyLoading", name: "Task 23: Lazy Loading", completed: false },
  {
    id: "unnecessaryRenders",
    name: "Task 24: Avoid Unnecessary Renders",
    completed: false,
  },
  {
    id: "customComparison",
    name: "Task 25: Custom Comparison",
    completed: false,
  },

  // UI Patterns
  { id: "modal", name: "Task 26: Modal Dialog", completed: false },
  { id: "autocomplete", name: "Task 27: Autocomplete", completed: false },
  { id: "carousel", name: "Task 28: Carousel", completed: false },
  { id: "dragDrop", name: "Task 29: Drag and Drop", completed: false },
  { id: "infiniteScroll", name: "Task 30: Infinite Scroll", completed: false },

  // Form & Validation
  {
    id: "dynamicFields",
    name: "Task 31: Dynamic Form Fields",
    completed: false,
  },
  { id: "multiStepForm", name: "Task 32: Multi-Step Form", completed: false },
  {
    id: "formValidationHook",
    name: "Task 33: Form Validation Hook",
    completed: false,
  },
  {
    id: "creditCardInput",
    name: "Task 34: Credit Card Input",
    completed: false,
  },
  {
    id: "passwordStrength",
    name: "Task 35: Password Strength Meter",
    completed: false,
  },

  // Animation & Styling
  {
    id: "notifications",
    name: "Task 36: Animated Notifications",
    completed: false,
  },
  { id: "themeSwitcher", name: "Task 37: Theme Switcher", completed: false },
  {
    id: "animatedAccordion",
    name: "Task 38: Animated Accordion",
    completed: false,
  },
  {
    id: "loadingSkeletons",
    name: "Task 39: Loading Skeletons",
    completed: false,
  },
  {
    id: "microInteractions",
    name: "Task 40: Micro-Interactions",
    completed: false,
  },

  // Accessibility
  {
    id: "keyboardNavigation",
    name: "Task 41: Keyboard Navigation",
    completed: false,
  },
  {
    id: "screenReaderFriendly",
    name: "Task 42: Screen Reader Friendly",
    completed: false,
  },
  { id: "focusTrap", name: "Task 43: Focus Trap", completed: false },
  {
    id: "colorContrast",
    name: "Task 44: Color Contrast Checker",
    completed: false,
  },
  {
    id: "accessibleErrors",
    name: "Task 45: Accessible Form Errors",
    completed: false,
  },
];

// Group tasks by category
export const taskCategories: TaskCategory[] = [
  { name: "Basic Components", tasks: tasks.slice(0, 5) },
  { name: "State Management", tasks: tasks.slice(5, 10) },
  { name: "Effects & Lifecycle", tasks: tasks.slice(10, 15) },
  { name: "Advanced Patterns", tasks: tasks.slice(15, 20) },
  { name: "Performance", tasks: tasks.slice(20, 25) },
  { name: "UI Patterns", tasks: tasks.slice(25, 30) },
  { name: "Forms & Validation", tasks: tasks.slice(30, 35) },
  { name: "Animation & Styling", tasks: tasks.slice(35, 40) },
  { name: "Accessibility", tasks: tasks.slice(40, 45) },
];

export default tasks;

export const longText = `Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.`;

export const AccordionMockData: AccordionItemType[] = [
  {
    id: "id-title-1",
    title: "Accordion 1",
    content: "Content for accordion 01",
  },
  {
    id: "id-title-2",
    title: "Accordion 2",
    content: "Content for accordion 02",
  },
  {
    id: "id-title-3",
    title: "Accordion 3",
    content: "Content for accordion 03",
  },
];

export const TabDummyContent = ({ text }: { text: string }) => {
  return (
    <div>
      <h3>Tab Dummy component</h3>
      <p>{text}</p>
    </div>
  );
};

export const TabData: TabItemType[] = [
  {
    id: "tab-id-01",
    tabTitle: "Tab 01",
    tabContent: <TabDummyContent text="Tab content 01" />,
  },
  {
    id: "tab-id-02",
    tabTitle: "Tab 02",
    tabContent: <TabDummyContent text="Tab content 02" />,
  },
  {
    id: "tab-id-03",
    tabTitle: "Tab 03",
    tabContent: <TabDummyContent text="Tab content 03" />,
  },
];
