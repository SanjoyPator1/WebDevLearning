function UseCallbackImplementation() {
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
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `useCallback` to memoize callback functions</li>
          <li>Optimize child rendering with `React.memo`</li>
        </ul>
      </div>
    </div>
  );
}

export default UseCallbackImplementation;
