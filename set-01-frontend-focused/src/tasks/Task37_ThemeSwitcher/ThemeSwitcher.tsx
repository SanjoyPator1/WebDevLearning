function ThemeSwitcher() {
  return (
    <div className="task-container">
      <h2>Task 37: Theme Switcher</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a theme switcher (light/dark mode)</li>
          <li>Persist the selected theme in `localStorage`</li>
          <li>Apply the theme to the entire application</li>
        </ul>
      </div>

      <div className="implementation">{/* Implementation goes here */}</div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use `useState` to manage the theme</li>
          <li>Use `useEffect` to sync with `localStorage`</li>
        </ul>
      </div>
    </div>
  );
}

export default ThemeSwitcher;
