import { useState } from "react";

function Counter() {
  const [counter, setCounter] = useState(0);

  const handleUpdateCounter = (type: "increment" | "decrement") => {
    // for accurate previous value use prev
    // for better code use guard clause
    setCounter((prev) => {
      if (type === "increment") return prev + 1;
      return prev > 0 ? prev - 1 : 0;
    });
    // used ternary for simpler and readable code
  };

  const handleReset = () => {
    setCounter(0);
  };

  return (
    <div className="task-container">
      <h2>Task 1: Counter Component</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a counter with increment and decrement buttons</li>
          <li>Initial count starts at 0</li>
          <li>Counter cannot go below 0</li>
          <li>Include a reset button</li>
        </ul>
      </div>

      <div className="implementation flex flex-col gap-3">
        <div className="">
          <h4>Counter:</h4>
          <p className="text-5xl">{counter}</p>
        </div>
        <div className="flex ">
          <button onClick={() => handleUpdateCounter("increment")}>
            + (increment)
          </button>
          <button onClick={() => handleUpdateCounter("decrement")}>
            - (decrement)
          </button>
          <button onClick={handleReset}>0 (reset)</button>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            React's <code>useState</code> hook is used to track mutable state in
            a functional component.
          </li>
          <li>
            <code>useState</code> returns an array with two elements: the
            current state and a function to update it.
          </li>
          <li>
            To safely update state based on its previous value, use the
            functional form: <code>{`setState(prev => ...)`}</code>.
          </li>
          <li>
            We use a unified handler function <code>handleUpdateCounter</code>{" "}
            that accepts a type ("increment" or "decrement") to decide the
            operation.
          </li>
          <li>
            To prevent the counter from going below zero, we use a condition to
            check the current value before decrementing.
          </li>
          <li>
            Added a <code>Reset</code> button to return the counter to its
            initial state (0).
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Counter;
