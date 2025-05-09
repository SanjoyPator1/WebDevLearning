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

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use libraries like `react-window` or `react-virtualized`</li>
          <li>Optimize performance with `useCallback` and `React.memo`</li>
        </ul>
      </div>
    </div>
  );
}

export default OptimizedListRendering;
