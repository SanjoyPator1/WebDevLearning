function CustomComparisonFunction() {
  return (
    <div className="task-container">
      <h2>Task 25: Custom Comparison Function</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a component using a custom comparison in `React.memo`</li>
          <li>Component receives a complex prop (array or object)</li>
          <li>Implement a custom comparison function for `React.memo`</li>
          <li>Toggle between default and custom comparison</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `React.memo` with a custom comparison function</li>
          <li>Handle deep comparison for complex props</li>
        </ul>
      </div>
    </div>
  );
}

export default CustomComparisonFunction;
