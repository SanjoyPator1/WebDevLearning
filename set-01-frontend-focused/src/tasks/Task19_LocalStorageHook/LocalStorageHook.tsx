import useLocalStorage from "./useLocalStorage";

function CustomHookWithLocalStorage() {
  const [theme, setTheme] = useLocalStorage<"light" | "dark">(
    "theme-dummy",
    "light"
  );

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
  };

  return (
    <div className="task-container">
      <h2>Task 19: Custom Hook with localStorage</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Implement a `useLocalStorage` hook</li>
          <li>Save and retrieve values from `localStorage`</li>
          <li>Update `localStorage` when state changes</li>
        </ul>
      </div>

      <div className="implementation">
        <div>
          <div>Current Theme : {theme}</div>
          <div>
            <p>change the theme:</p>
            <button
              onClick={toggleTheme}
              className="btn btn-primary"
              aria-label="Toggle theme"
            >
              {theme === "light" ? "dark" : "light"}
            </button>
          </div>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            The <code>useLocalStorage</code> hook uses <code>useState</code> and{" "}
            <code>useEffect</code> to manage and persist state.
          </li>
          <li>
            When the component mounts, it tries to load the value from{" "}
            <code>localStorage</code>. If not found, it falls back to the
            provided default value.
          </li>
          <li>
            Any state updates are automatically saved to{" "}
            <code>localStorage</code> using <code>JSON.stringify</code> for
            serialization.
          </li>
          <li>
            On updates, the stored value is deserialized with{" "}
            <code>JSON.parse</code> to ensure correct data types.
          </li>
          <li>
            The hook also listens for changes from other browser tabs and
            updates the state accordingly to stay in sync.
          </li>
          <li>
            Supports TypeScript generics to enforce type safety for stored
            values.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default CustomHookWithLocalStorage;
