function AvoidingUnnecessaryRenders() {
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

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `React.memo` to optimize child components</li>
          <li>Ensure props dependencies are correctly managed</li>
        </ul>
      </div>
    </div>
  );
}

export default AvoidingUnnecessaryRenders;
