import { useCallback, useState } from "react";
import MemoizedCounter from "./Counter";
import MessageCard from "./MessageCard";

type IncrementType = "increment" | "decrement"

function AvoidingUnnecessaryRenders() {
  const [counter, setCounter] = useState(0)
  const [message, setMessage] = useState("initial message")

  // simple incremet decrement function without callback
  const handleUpdateCount = useCallback((mode: IncrementType) => {
    setCounter((prev) => mode === "increment" ? prev + 1 : prev - 1)
  }, [])

  const handleUpdateMessage = useCallback((newMessage: string) => {
    setMessage(newMessage)
  }, [])

  return (
    <div className="task-container">
      <h2>Task 24: Avoiding Unnecessary Renders</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Fix a component with unnecessary render problems</li>
          <li>Parent component with multiple state variables</li>
          <li>Multiple child components depend on specific props</li>
          <li>
            Optimize to prevent children re-rendering when unrelated state
            changes
          </li>
        </ul>
      </div>

      <div className="implementation space-y-3">
        {/* Only rerenders if count changes */}
        <MemoizedCounter counter={counter} handleCounter={handleUpdateCount} />

        {/* Only rerenders if message changes */}
        <MessageCard message={message} updateMessage={handleUpdateMessage} />
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul className="list-disc pl-5 space-y-2">
          <li>
            Used <code>React.memo</code> to memoize <code>Counter</code> and <code>MessageCard</code> components, so they only re-render when their specific props change.
          </li>
          <li>
            Applied <code>useCallback</code> to memoize <code>handleUpdateCount</code> and <code>handleUpdateMessage</code> functions, ensuring stable references between renders.
          </li>
          <li>
            Separated concerns by maintaining <code>counter</code> and <code>message</code> in distinct state variables. Each child component is responsible only for the state it uses.
          </li>
          <li>
            Verified rendering behavior using <code>console.log</code> inside child components to confirm they only render on relevant prop updates.
          </li>
          <li>
            Used Tailwind utility classes for clean, reusable, and responsive UI styling across all components.
          </li>
          <li>
            Added accessibility attribute <code>aria-label</code> to input field for better accessibility support.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default AvoidingUnnecessaryRenders;
