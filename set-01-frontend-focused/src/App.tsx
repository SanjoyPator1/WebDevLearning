import { useState } from "react";
import "./App.css";
import TaskList from "./components/TaskList";
import TaskRenderer from "./components/TaskRenderer/index.tsx";

function App() {
  const [currentTask, setCurrentTask] = useState<string | null>(null);

  return (
    <div className="app-container">
      <header>
        <h1>React Interview Practice</h1>
        <p className="subtitle">
          A collection of 45 progressively challenging tasks
        </p>
      </header>

      <div className="content">
        <aside className="sidebar">
          <TaskList currentTask={currentTask} setCurrentTask={setCurrentTask} />
        </aside>

        <main className="task-display">
          <TaskRenderer currentTask={currentTask} />
        </main>
      </div>

      <footer>
        <p>React TypeScript Practice - {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}

export default App;
