function ModalDialog() {
  return (
    <div className="task-container">
      <h2>Task 26: Modal Dialog</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a modal dialog component</li>
          <li>Include open and close functionality</li>
          <li>Overlay should close the modal when clicked</li>
          <li>Support keyboard accessibility (e.g., Escape key to close)</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `useState` to manage modal visibility</li>
          <li>Handle keyboard events for accessibility</li>
        </ul>
      </div>
    </div>
  );
}

export default ModalDialog;
