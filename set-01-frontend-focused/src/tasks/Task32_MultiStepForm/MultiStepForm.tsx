function MultiStepForm() {
  return (
    <div className="task-container">
      <h2>Task 32: Multi-Step Form</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a multi-step form</li>
          <li>Include navigation between steps</li>
          <li>Persist data across steps</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `useState` to manage form data</li>
          <li>Render different steps conditionally</li>
        </ul>
      </div>
    </div>
  );
}

export default MultiStepForm;
