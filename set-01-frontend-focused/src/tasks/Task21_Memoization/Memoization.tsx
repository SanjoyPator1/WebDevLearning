import React, { useMemo, useState } from "react";

function MemoizationPractice() {
  const [inputNumber, setInputNumber] = useState<number>(0);
  const [counter, setCounter] = useState(0);

  const fibonacciNumbers = useMemo(() => {
    const sequence = [0, 1];

    for (let i = 2; i <= inputNumber; i++) {
      sequence.push(sequence[i - 1] + sequence[i - 2]);
    }

    return sequence.slice(0, inputNumber + 1);
  }, [inputNumber]);

  return (
    <div className="task-container">
      <h2>Task 21: Memoization Practice</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a component with expensive calculations</li>
          <li>Input field for a number</li>
          <li>
            Calculate and display the Fibonacci sequence up to that number
          </li>
          <li>Use `useMemo` to memoize the calculation</li>
          <li>Add unrelated state to demonstrate memoization effectiveness</li>
        </ul>
      </div>

      <div className="implementation space-y-4">
        <div>
          {/* input field */}
          <div>
            <input
              value={inputNumber ?? 0}
              type="number"
              placeholder="type your number"
              onChange={(e) => setInputNumber(Number(e.target.value))}
            />
          </div>
          <div>
            <h5>Fibonacci numbers:</h5>
            <span>
              {fibonacciNumbers.map((num) => {
                return <React.Fragment key={num}>{num}, </React.Fragment>;
              })}
            </span>
          </div>
        </div>
        <div className="space-y-2">
          Count : {counter}
          <div className="w-fit flex gap-2">
            <button
              onClick={() => setCounter((prev) => (prev -= 1))}
              className="btn btn-primary"
            >
              -
            </button>
            <button
              onClick={() => setCounter((prev) => (prev += 1))}
              className="btn btn-primary"
            >
              +
            </button>
          </div>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            <code>useMemo</code> is a React Hook that memoizes the result of an
            expensive calculation. It only recalculates the value when one of
            its dependencies changes, which helps optimize performance.
          </li>
          <li>
            The <strong>dependency array</strong> (the second argument to{" "}
            <code>useMemo</code>) determines when the memoized value should be
            recomputed. In this example, <code>[inputNumber]</code> is used, so
            the Fibonacci sequence is only recalculated when{" "}
            <code>inputNumber</code> changes.
          </li>
          <li>
            You <strong>do not need extra state</strong> for the Fibonacci
            numbers. The value returned by <code>useMemo</code> can be used
            directly in your JSX, making your component simpler and more
            efficient.
          </li>
          <li>
            Unrelated state changes (like updating the counter) do{" "}
            <strong>not</strong> trigger recalculation of the Fibonacci
            sequence, because they are not included in the dependency array.
          </li>
          <li>
            <code>useMemo</code> is especially useful for optimizing components
            that perform expensive calculations or render large lists, as it
            prevents unnecessary recalculations and re-renders.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default MemoizationPractice;
