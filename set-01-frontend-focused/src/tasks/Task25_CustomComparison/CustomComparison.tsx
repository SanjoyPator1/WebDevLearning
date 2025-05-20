import { useState } from "react";
import MemoizedSettings from "./Settings";
import MemoizedTodo from "./Todo";

export type SettingsInitialDataType = {
  theme: string;
  notifications: boolean;
  fontSize: number;
}


const settingsInitialData: SettingsInitialDataType = {
  theme: "dark",
  notifications: true,
  fontSize: 14,
};

export type TodoType = {
  id: number;
  task: string;
  done: boolean;
}


const todoItems: TodoType[] = [
  { id: 1, task: "Learn React", done: false },
  { id: 2, task: "Write Code", done: true },
];


function CustomComparisonFunction() {

  // object complex prop
  const [settings, setSettings] = useState<SettingsInitialDataType>(settingsInitialData)

  // array complex prop
  const [todo, setTodo] = useState<TodoType[]>(todoItems)

  const handleUpdateSettings = () => {
    setSettings(
      (prev) => ({
        theme: "dark",
        notifications: true,
        fontSize: prev.fontSize + 1,
      })
    )
  }

  const handleUpdateTodo = () => {
    setTodo((prev) => (
      [
        ...prev,
        {
          id: prev.length + 1,
          task: `New Task ${prev.length + 1}`,
          done: false,
        }
      ]
    ))
  }


  return (
    <div className="task-container">
      <h2>Task 25: Custom Comparison Function</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a component using a custom comparison in `React.memo`</li>
          <li>Component receives a complex prop (array or object)</li>
          <li>Implement a custom comparison function for `React.memo`</li>
          <li>Toggle between default and custom comparison</li>
        </ul>
      </div>

      <div className="implementation space-y-3">
        <div className="border p-2">
          <p>first child component with object prop</p>
          <MemoizedSettings data={settings} />
        </div>

        <div className="border p-2">
          <p>second child component with array prop</p>
          <MemoizedTodo data={todo} />
        </div>

        <div className="space-y-2">
          <p>Update values</p>
          <div className="space-x-2">

            <button className="btn btn-primary" onClick={handleUpdateSettings}>update settings</button>
            <button className="btn btn-primary" onClick={handleUpdateTodo}>update todos</button>
          </div>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul className="space-y-2">
          <li><strong>Goal:</strong> Use <code>React.memo</code> with a custom comparison function to prevent unnecessary re-renders.</li>
          <li><strong>Settings Component:</strong> Accepts an <code>object</code> prop; compares each field individually (theme, notifications, fontSize).</li>
          <li><strong>Todo Component:</strong> Accepts an <code>array</code> prop; deeply compares each todo item for changes.</li>
          <li><strong>React.memo:</strong> Skips re-render if the custom comparison returns <code>true</code>.</li>
          <li><strong>Test:</strong> Use the "Update" buttons to trigger updates and check which components rerender (via console logs).</li>
          <li><strong>Why:</strong> Custom comparison helps optimize renders when shallow equality isn't sufficient (objects/arrays).</li>
        </ul>
      </div>

    </div>
  );
}

export default CustomComparisonFunction;
