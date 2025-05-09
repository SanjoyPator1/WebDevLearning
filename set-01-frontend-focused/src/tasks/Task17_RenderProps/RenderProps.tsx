function RenderPropsPattern() {
  return (
    <div className="task-container">
      <h2>Task 17: Render Props Pattern</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a `HoverCard` component that accepts render props</li>
          <li>Detect mouse hover over an element</li>
          <li>Show additional content on hover</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `useState` to track hover state</li>
          <li>Pass hover state to children via render props</li>
        </ul>
      </div>
    </div>
  );
}

export default RenderPropsPattern;
