import { useCallback, useState } from "react";
import MemoizedCounter from "./Counter";

type IncrementType = "increment" | "decrement"

function UseCallbackImplementation() {
  const [countStateOne, setCountStateOne] = useState(0)
  const [countStateTwo, setCountStateTwo] = useState(0)
  const [countStateThree, setCountStateThree] = useState(0)
  const [stepState, setStepState] = useState(1)

  // simple incremet decrement function without callback
  const handleUpdateCountOne = (mode: IncrementType) => {
    setCountStateOne((prev) => mode === "increment" ? prev + 1 : prev - 1)
  }

  // enhanced incremet decrement function with callback with no dependency
  const handleUpdateCountTwo = useCallback((mode: IncrementType) => {
    setCountStateTwo((prev) => mode === "increment" ? prev + 1 : prev - 1)
  }, [])

  // enhanced incremet decrement function with callback with step dependency
  const handleUpdateCountThree = useCallback((mode: IncrementType) => {
    setCountStateThree((prev) => mode === "increment" ? prev + stepState : prev - stepState)
  }, [stepState])


  return (
    <div className="task-container">
      <h2>Task 22: useCallback Implementation</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create parent and child components using `useCallback`</li>
          <li>Parent with multiple state variables</li>
          <li>Child receives a callback function</li>
          <li>Use `React.memo` on the child</li>
          <li>Compare behavior with and without `useCallback`</li>
          <li><strong>(Extra)</strong> Demonstrate a useCallback with a dependency (`stepState`) to show dynamic recalculations</li>
        </ul>
      </div>

      <div className="implementation space-y-4">
        <div className="space-y-3">
          <h4>Example 1: normal counter without useCallback</h4>
          <MemoizedCounter counter={countStateOne} handleCounter={handleUpdateCountOne} />
        </div>
        <div className="space-y-3">
          <h4>Example 2: enhanced counter with useCallback</h4>
          <MemoizedCounter counter={countStateTwo} handleCounter={handleUpdateCountTwo} />
        </div>
        <div className="space-y-3">
          <h4>Example 3: step counter with useCallback and step dependency</h4>
          <MemoizedCounter counter={countStateThree} handleCounter={handleUpdateCountThree} />
          <div className="flex flex-row gap-3">
            <label>Step to increment by : </label>
            <input
              type="number"
              value={stepState}
              placeholder="step for counter"
              onChange={(e) => {
                const value = Number(e.target.value);
                if (!isNaN(value)) setStepState(value);
              }}
            />
          </div>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul className="list-disc pl-5 space-y-2">
          <li>
            <strong>Why use <code>useCallback</code>:</strong> In React, functions are re-created on every render. If a function is passed to a memoized child component, it may cause unnecessary re-renders unless the function's reference remains stable. <code>useCallback</code> memoizes the function and ensures a stable reference across renders unless dependencies change.
          </li>
          <li>
            <strong>Example 1 (without <code>useCallback</code>):</strong> The callback <code>handleUpdateCountOne</code> is re-created on every render. Even if the prop data doesn’t change, the child component re-renders due to the new function reference.
          </li>
          <li>
            <strong>Example 2 (with <code>useCallback</code> and empty dependency array):</strong> <code>handleUpdateCountTwo</code> is only created once. This prevents unnecessary re-renders of the <code>MemoizedCounter</code> unless the component is re-mounted.
          </li>
          <li>
            <strong>Example 3 (with <code>useCallback</code> and dependency):</strong> <code>handleUpdateCountThree</code> depends on <code>stepState</code>. The function is re-created only when <code>stepState</code> changes. This shows how dependencies influence the memoization and how to control when callbacks should be updated.
          </li>
          <li>
            <strong>Using <code>React.memo</code>:</strong> The child component <code>MemoizedCounter</code> is wrapped in <code>React.memo</code>, which shallowly compares props. This works effectively with <code>useCallback</code> because it receives a stable function reference unless its logic actually changes.
          </li>
          <li>
            <strong>Best Practice:</strong> Combine <code>React.memo</code> and <code>useCallback</code> in performance-critical components, especially when passing callbacks to deeply nested children or frequently rendered components.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default UseCallbackImplementation;
