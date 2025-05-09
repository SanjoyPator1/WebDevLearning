import React from "react";
import "./TaskList.css";
import { taskCategories } from "../../shared/utils/tasksData";

interface TaskListProps {
  currentTask: string | null;
  setCurrentTask: (task: string) => void;
}

const TaskList: React.FC<TaskListProps> = ({ currentTask, setCurrentTask }) => {
  // Flatten all tasks for counting completions
  const allTasks = taskCategories.flatMap((category) => category.tasks);

  // Count completed tasks
  const completedCount = allTasks.filter((task) => task.completed).length;

  return (
    <div className="task-list">
      <h2>Tasks</h2>

      {taskCategories.map((category) => (
        <div key={category.name} className="task-category">
          <h3>{category.name}</h3>
          <ul>
            {category.tasks.map((task) => (
              <li
                key={task.id}
                className={`task-item ${
                  currentTask === task.id ? "active" : ""
                } ${task.completed ? "completed" : ""}`}
                onClick={() => setCurrentTask(task.id)}
              >
                {task.name}
              </li>
            ))}
          </ul>
        </div>
      ))}

      <div className="progress">
        <p>
          Completed: {completedCount} / {allTasks.length}
        </p>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${(completedCount / allTasks.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default TaskList;
