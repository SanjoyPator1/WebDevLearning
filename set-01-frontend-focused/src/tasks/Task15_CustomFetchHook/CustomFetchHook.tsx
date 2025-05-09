function CustomUseFetchHook() {
    return (
      <div className="task-container">
        <h2>Task 15: Custom useFetch Hook</h2>
  
        <div className="task-description">
          <h3>Requirements:</h3>
          <ul>
            <li>Create a reusable `useFetch` hook for API calls</li>
            <li>Handle loading, error, and success states</li>
            <li>Accept a timeout parameter to control delay</li>
          </ul>
        </div>
  
        <div className="implementation">{/* Implementation goes here */}</div>
  
        <div className="task-notes">
          <h3>Implementation Notes:</h3>
          <ul>
            <li>Use `useState` and `useEffect` to manage the hook's behavior</li>
            <li>Simulate API calls with `setTimeout`</li>
          </ul>
        </div>
      </div>
    );
  }
  
  export default CustomUseFetchHook;