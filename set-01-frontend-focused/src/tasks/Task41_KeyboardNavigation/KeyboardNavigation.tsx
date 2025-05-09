function KeyboardNavigation() {
  return (
    <div className="task-container">
      <h2>Task 41: Keyboard Navigation</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Enable keyboard navigation for a list or menu</li>
          <li>Highlight the active item as the user navigates</li>
          <li>Support Enter key to select an item</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `onKeyDown` to handle keyboard events</li>
          <li>Manage the active item with `useState`</li>
        </ul>
      </div>
    </div>
  );
}

export default KeyboardNavigation;
