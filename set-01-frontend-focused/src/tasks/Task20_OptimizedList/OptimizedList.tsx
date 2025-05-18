// OptimizedListRendering.tsx
import ComplexListImplementation from "./ComplexListImplementation";
import DynamicSizeListImplementation from "./DynamicSizeListImplementation";
import FixedSizeListImplementation from "./FixedSizeListImplementation";

function OptimizedListRendering() {
  return (
    <div className="task-container">
      <h2 className="text-2xl font-bold mb-4">
        Task 20: Optimized List Rendering
      </h2>

      <div className="task-description mb-6 bg-gray-50 p-4 rounded-lg">
        <h3 className="text-xl font-semibold mb-2">Requirements:</h3>
        <ul className="list-disc ml-6 space-y-1">
          <li>Render a list with 1000+ items</li>
          <li>Use `React.memo` to prevent unnecessary renders</li>
          <li>
            Implement virtualized list rendering (show only visible items)
          </li>
        </ul>
      </div>

      <div className="implementations space-y-10">
        {/* Fixed Size List Implementation */}
        <div className="implementation-section">
          <h3 className="text-xl font-semibold mb-3">
            1. Fixed Size List Implementation
          </h3>
          <div className="border rounded-lg shadow h-64 overflow-hidden mb-4">
            <FixedSizeListImplementation />
          </div>
          <div className="bg-blue-50 p-3 rounded">
            <ul className="list-disc list-inside text-gray-700 space-y-2">
              <li>
                <span className="font-medium">
                  Basic virtualization with{" "}
                  <code className="bg-gray-100 px-1 rounded">
                    FixedSizeList
                  </code>
                  :
                </span>
                <p className="ml-4 mt-1 text-sm text-gray-600">
                  Uses react-window's FixedSizeList for efficient rendering of
                  large lists with consistent item heights. Perfect for simple
                  lists where all items have the same height.
                </p>
              </li>
              <li>
                <span className="font-medium">Simple memoization:</span>
                <p className="ml-4 mt-1 text-sm text-gray-600">
                  Basic React.memo implementation prevents unnecessary
                  re-renders when scrolling or when parent components update.
                </p>
              </li>
            </ul>
          </div>
        </div>

        {/* Dynamic Size List Implementation */}
        <div className="implementation-section">
          <h3 className="text-xl font-semibold mb-3">
            2. Dynamic Size List Implementation
          </h3>
          <div className="border rounded-lg shadow h-64 overflow-hidden mb-4">
            <DynamicSizeListImplementation />
          </div>
          <div className="bg-blue-50 p-3 rounded">
            <ul className="list-disc list-inside text-gray-700 space-y-2">
              <li>
                <span className="font-medium">
                  Content-adaptive heights with{" "}
                  <code className="bg-gray-100 px-1 rounded">
                    VariableSizeList
                  </code>
                  :
                </span>
                <p className="ml-4 mt-1 text-sm text-gray-600">
                  Uses react-window's VariableSizeList to allow each item to
                  have its own height based on content. Ideal for text of
                  varying lengths.
                </p>
              </li>
              <li>
                <span className="font-medium">
                  Height measurement and caching:
                </span>
                <p className="ml-4 mt-1 text-sm text-gray-600">
                  Measures actual rendered item heights and caches them for
                  smooth scrolling. Automatically adjusts estimated heights
                  based on content.
                </p>
              </li>
            </ul>
          </div>
        </div>

        {/* Complex List Implementation */}
        <div className="implementation-section">
          <h3 className="text-xl font-semibold mb-3">
            3. Complex List Implementation
          </h3>
          <div className="border rounded-lg shadow h-64 overflow-hidden mb-4">
            <ComplexListImplementation />
          </div>
          <div className="bg-blue-50 p-3 rounded">
            <ul className="list-disc list-inside text-gray-700 space-y-2">
              <li>
                <span className="font-medium">
                  Advanced memoization with custom comparison:
                </span>
                <p className="ml-4 mt-1 text-sm text-gray-600">
                  Uses a custom comparison function with React.memo that
                  intelligently determines when a re-render is needed based on
                  which specific properties changed. Handles complex data types
                  like arrays and dates correctly.
                </p>
              </li>
              <li>
                <span className="font-medium">
                  Rich UI with multiple data points:
                </span>
                <p className="ml-4 mt-1 text-sm text-gray-600">
                  Renders complex items with multiple properties including
                  priority indicators, tags, completion status, and timestamps.
                  Demonstrates how to maintain performance with visually rich
                  components.
                </p>
              </li>
              <li>
                <span className="font-medium">Optimized update patterns:</span>
                <p className="ml-4 mt-1 text-sm text-gray-600">
                  Prevents unnecessary re-renders when only non-visual
                  properties change. Perfect for data-heavy applications where
                  only some property changes affect UI.
                </p>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-10 bg-gray-50 p-4 rounded-lg">
        <h3 className="text-xl font-semibold text-gray-800 mb-2">
          Overall Implementation Notes:
        </h3>
        <ul className="list-disc list-inside text-gray-700 space-y-2">
          <li>
            <span className="font-medium">Virtualized Rendering:</span>
            <p className="ml-4 mt-1 text-sm text-gray-600">
              All implementations use react-window to efficiently render large
              lists by only keeping DOM nodes for visible items plus a small
              overscan area. This drastically reduces memory usage and improves
              performance for lists with 1000+ items.
            </p>
          </li>
          <li>
            <span className="font-medium">
              Selective Re-rendering with React.memo:
            </span>
            <p className="ml-4 mt-1 text-sm text-gray-600">
              All implementations use React.memo to prevent unnecessary
              re-renders, with increasing levels of sophistication from basic to
              custom deep comparison.
            </p>
          </li>
          <li>
            <span className="font-medium">Progressive Enhancement:</span>
            <p className="ml-4 mt-1 text-sm text-gray-600">
              The three implementations show a progression from simple to
              advanced techniques, allowing developers to choose the approach
              that best matches their use case and performance requirements.
            </p>
          </li>
          <li>
            <span className="font-medium">TypeScript Integration:</span>
            <p className="ml-4 mt-1 text-sm text-gray-600">
              All implementations use TypeScript to ensure type safety and
              improve code quality. Proper interfaces are defined for component
              props and data structures.
            </p>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default OptimizedListRendering;
