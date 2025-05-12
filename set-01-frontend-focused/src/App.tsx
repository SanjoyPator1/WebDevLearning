import { useState, useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useParams,
  useNavigate,
} from "react-router-dom";
import "./App.css";
import TaskList from "./components/TaskList";
import TaskRenderer from "./components/TaskRenderer";
import NotFound from "./components/NotFound";
import { taskCategories } from "./shared/utils/tasksData";

// Helper function to check if a task ID is valid
const isValidTaskId = (taskId: string | null | undefined): boolean => {
  if (!taskId) return false;
  if (taskId === "welcome") return true;
  return taskCategories.some((category) =>
    category.tasks.some((task) => task.id === taskId)
  );
};

// Task route component
function TaskRoute() {
  const { taskId } = useParams<{ taskId?: string }>();
  const navigate = useNavigate();

  // Initialize with null, then update after validation in useEffect
  const [currentTask, setCurrentTask] = useState<string | null>(null);

  // Handle task selection changes
  const handleTaskChange = (task: string) => {
    setCurrentTask(task);
    navigate(`/task/${task}`);
  };

  // Update currentTask when URL changes or on initial load
  useEffect(() => {
    if (taskId && isValidTaskId(taskId)) {
      setCurrentTask(taskId);
    } else if (taskId) {
      // If taskId exists but is invalid, keep it null (will show NotFound)
      setCurrentTask(null);
    }
  }, [taskId]);

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
          <TaskList
            currentTask={currentTask}
            setCurrentTask={handleTaskChange}
          />
        </aside>

        <main className="task-display">
          {taskId && !isValidTaskId(taskId) ? (
            <NotFound type="task" taskId={taskId} />
          ) : (
            <TaskRenderer currentTask={currentTask} />
          )}
        </main>
      </div>

      <footer>
        <p>React TypeScript Practice - {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}

// Page not found component for entire pages
function PageNotFound() {
  return (
    <div className="app-container">
      <header>
        <h1>React Interview Practice</h1>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center min-h-[70vh] p-5">
        <NotFound type="page" />
      </div>

      <footer>
        <p>React TypeScript Practice - {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}

// Home route that redirects to the welcome page
function HomeRoute() {
  return <Navigate to="/task/welcome" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomeRoute />} />
        <Route path="/task/:taskId" element={<TaskRoute />} />
        <Route path="*" element={<PageNotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
