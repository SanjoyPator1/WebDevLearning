function WindowSizeTracker() {
    return (
      <div className="task-container">
        <h2>Task 13: Window Size Tracker</h2>
  
        <div className="task-description">
          <h3>Requirements:</h3>
          <ul>
            <li>Display the current width and height of the browser window</li>
            <li>Update the dimensions when the window is resized</li>
          </ul>
        </div>
  
        <div className="implementation">{/* Implementation goes here */}</div>
  
        <div className="task-notes">
          <h3>Implementation Notes:</h3>
          <ul>
            <li>Use `useEffect` to add and clean up the resize event listener</li>
            <li>Use `useState` to store the window dimensions</li>
          </ul>
        </div>
      </div>
    );
  }
  
  export default WindowSizeTracker;