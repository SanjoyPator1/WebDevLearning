function CompoundComponentPattern() {
    return (
      <div className="task-container">
        <h2>Task 16: Compound Component Pattern</h2>
  
        <div className="task-description">
          <h3>Requirements:</h3>
          <ul>
            <li>Create a custom select component using compound components</li>
            <li>Clicking the select opens a dropdown</li>
            <li>Selecting an option updates the parent value</li>
            <li>Close the dropdown when clicking outside</li>
          </ul>
        </div>
  
        <div className="implementation">{/* Implementation goes here */}</div>
  
        <div className="task-notes">
          <h3>Implementation Notes:</h3>
          <ul>
            <li>Use `React.Children` and context for compound components</li>
            <li>Handle dropdown visibility with `useState`</li>
          </ul>
        </div>
      </div>
    );
  }
  
  export default CompoundComponentPattern;