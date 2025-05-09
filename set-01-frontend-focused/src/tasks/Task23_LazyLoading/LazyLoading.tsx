function ReactLazyAndCodeSplitting() {
  return (
    <div className="task-container">
      <h2>Task 23: React.lazy and Code Splitting</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create multiple page components</li>
          <li>Use `React.lazy` to load them dynamically</li>
          <li>Add `Suspense` with a fallback loader</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `React.lazy` for dynamic imports</li>
          <li>Wrap lazy-loaded components with `Suspense`</li>
        </ul>
      </div>
    </div>
  );
}

export default ReactLazyAndCodeSplitting;
