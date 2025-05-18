import { FixedSizeList } from "react-window";
import MemoizedListItem from "./ListItem";

const itemCount = 1000;
const itemHeight = 40;

function OptimizedListRendering() {
  return (
    <div className="task-container">
      <h2>Task 20: Optimized List Rendering</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Render a list with 1000+ items</li>
          <li>Use `React.memo` to prevent unnecessary renders</li>
          <li>
            Implement virtualized list rendering (show only visible items)
          </li>
        </ul>
      </div>

      <div className="implementation space-y-3">
        <div className="border rounded shadow h-96 overflow-hidden mb-6 space-y-2">
          <h4 className="p-2">Fixed size list</h4>
          <FixedSizeList
            height={384} // 96 * 4 (rem height)
            itemCount={itemCount}
            itemSize={itemHeight}
            width={"100%"}
          >
            {({ index, style }) => (
              <div style={style}>
                <MemoizedListItem index={index} />
              </div>
            )}
          </FixedSizeList>
        </div>
      </div>

      <div className="mt-8">
        <h3 className="text-xl font-semibold text-gray-800 mb-2">
          Implementation Notes:
        </h3>
        <ul className="list-disc list-inside text-gray-700 space-y-2">
          <li>
            <span className="font-medium">
              Virtualized Rendering with{" "}
              <code className="bg-gray-100 px-1 rounded">react-window</code>:
            </span>
            <p className="ml-4 mt-1 text-sm text-gray-600">
              Instead of rendering all 1000+ items at once, which would
              significantly impact performance, we used the{" "}
              <code className="bg-gray-100 px-1 rounded">FixedSizeList</code>{" "}
              component from the
              <code className="bg-gray-100 px-1 rounded">
                react-window
              </code>{" "}
              library. This ensures that only the visible portion of the list is
              rendered in the DOM, drastically reducing rendering cost and
              memory usage.
            </p>
          </li>
          <li>
            <span className="font-medium">
              Memoized List Items with{" "}
              <code className="bg-gray-100 px-1 rounded">React.memo</code>:
            </span>
            <p className="ml-4 mt-1 text-sm text-gray-600">
              Each individual list item is wrapped with{" "}
              <code className="bg-gray-100 px-1 rounded">React.memo</code>
              to prevent unnecessary re-renders when the item's props haven't
              changed. This is especially beneficial when dealing with large
              lists, ensuring smooth scrolling and optimized performance.
            </p>
          </li>
          <li>
            <span className="font-medium">Separation of Concerns:</span>
            <p className="ml-4 mt-1 text-sm text-gray-600">
              The list item was extracted into a standalone component to isolate
              rendering logic and apply memoization cleanly. This also improves
              readability, testability, and reusability of the code.
            </p>
          </li>
          <li>
            <span className="font-medium">
              Clean Styling with Tailwind CSS:
            </span>
            <p className="ml-4 mt-1 text-sm text-gray-600">
              Tailwind utility classes were used to style the list and items
              concisely and responsively, without relying on custom CSS. It
              keeps the design consistent and easy to adjust.
            </p>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default OptimizedListRendering;
