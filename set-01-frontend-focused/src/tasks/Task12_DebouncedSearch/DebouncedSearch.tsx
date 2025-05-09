function DebouncedSearch() {
    return (
      <div className="task-container">
        <h2>Task 12: Debounced Search</h2>
  
        <div className="task-description">
          <h3>Requirements:</h3>
          <ul>
            <li>Create a search input with debounced functionality</li>
            <li>Perform search only after user stops typing for 500ms</li>
            <li>Use mock data for search results</li>
          </ul>
        </div>
  
        <div className="implementation">{/* Implementation goes here */}</div>
  
        <div className="task-notes">
          <h3>Implementation Notes:</h3>
          <ul>
            <li>Use `useEffect` and `setTimeout` for debouncing</li>
            <li>Clear the timeout on component unmount or input change</li>
          </ul>
        </div>
      </div>
    );
  }
  
  export default DebouncedSearch;