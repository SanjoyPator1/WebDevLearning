function MemoizationPractice() {
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

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `useMemo` to optimize expensive calculations</li>
          <li>Ensure unrelated state changes do not trigger recalculations</li>
        </ul>
      </div>
    </div>
  );
}

export default MemoizationPractice;
