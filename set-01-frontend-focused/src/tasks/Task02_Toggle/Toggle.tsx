import { useState } from "react";

type BackgroundType = "on" | "off";

function Toggle() {
  const [background, setBackground] = useState<BackgroundType>("off");

  const handleToggleBackground = () => {
    setBackground((prev) => (prev === "on" ? "off" : "on"));
  };

  return (
    <div className="task-container">
      <h2>Task 2: Toggle Component</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a button that toggles between ON and OFF states</li>
          <li>Button text should change based on the current state</li>
          <li>Background color should change based on the current state</li>
        </ul>
      </div>

      <div
        className={`min-h-32 rounded-md flex items-center justify-center transition-all ${
          background === "on" ? "bg-amber-300" : "bg-amber-100/50"
        }`}
      >
        <button
          onClick={handleToggleBackground}
          className="px-4 py-2 font-semibold rounded bg-white shadow"
        >
          {background === "on" ? "Turn OFF" : "Turn ON"}
        </button>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            We use <code>useState</code> to manage a state variable called{" "}
            <code>background</code>, which can be either <code>"on"</code> or{" "}
            <code>"off"</code>.
          </li>
          <li>
            The <code>handleToggleBackground</code> function toggles the state
            using a functional update:{" "}
            <code>prev =&gt; (prev === "on" ? "off" : "on")</code>.
          </li>
          <li>
            The background color of the component changes conditionally using a
            ternary operator inside the <code>className</code>.
          </li>
          <li>
            The button label dynamically reflects the opposite of the current
            state (e.g., if it's "on", the button says "Turn OFF").
          </li>
          <li>
            Using the <code>transition-all</code> class allows smooth visual
            transitions when the background changes.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Toggle;
