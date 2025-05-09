function Timer() {
  return (
    <div className="task-container">
      <h2>Task 11: Timer/Stopwatch</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a stopwatch with start, stop, and reset functions</li>
          <li>Display time in mm:ss format</li>
          <li>Include start, stop, and reset buttons</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `useEffect` for managing the timer interval</li>
          <li>Ensure proper cleanup of intervals to avoid memory leaks</li>
        </ul>
      </div>
    </div>
  );
}

export default Timer;