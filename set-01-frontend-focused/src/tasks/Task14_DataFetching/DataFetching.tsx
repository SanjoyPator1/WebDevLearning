function DataFetchingSimulation() {
    return (
      <div className="task-container">
        <h2>Task 14: Data Fetching Simulation</h2>
  
        <div className="task-description">
          <h3>Requirements:</h3>
          <ul>
            <li>Simulate data fetching with an artificial delay</li>
            <li>Show a loading state while fetching</li>
            <li>Handle success and error states</li>
          </ul>
        </div>
  
        <div className="implementation">{/* Implementation goes here */}</div>
  
        <div className="task-notes">
          <h3>Implementation Notes:</h3>
          <ul>
            <li>Use `setTimeout` to simulate a network request</li>
            <li>Use `useState` to manage loading, success, and error states</li>
          </ul>
        </div>
      </div>
    );
  }
  
  export default DataFetchingSimulation;