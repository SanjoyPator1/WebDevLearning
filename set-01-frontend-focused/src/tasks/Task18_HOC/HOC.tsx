function HigherOrderComponents() {
  return (
    <div className="task-container">
      <h2>Task 18: Higher Order Components</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a `withLoading` HOC</li>
          <li>Wrapped components should show a spinner while loading</li>
          <li>Pass the loading state into the wrapped component</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use function composition to create the HOC</li>
          <li>Pass props from the HOC to the wrapped component</li>
        </ul>
      </div>
    </div>
  );
}

export default HigherOrderComponents;
