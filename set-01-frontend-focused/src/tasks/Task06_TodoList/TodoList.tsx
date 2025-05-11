import { X } from "lucide-react";
import { useState } from "react";

export type PriorityType = "low" | "medium" | "high";

export type TodoItemType = {
  id: string | number;
  text: string;
  completed: boolean;
  priority: PriorityType;
};

export type TodoListProps = {
  todoData: TodoItemType[];
};

type TodoItemProps = {
  todoItemData: TodoItemType;
  handleToggleCompletion: (id: number | string) => void;
  handleUpdatePriority: (id: string | number, priority: PriorityType) => void;
  handleDeleteTodo: (id: string | number) => void;
};

const TodoItem: React.FC<TodoItemProps> = ({
  todoItemData,
  handleToggleCompletion,
  handleUpdatePriority,
  handleDeleteTodo,
}) => {
  return (
    <div className="flex gap-2 justify-between border rounded-md py-2 px-4">
      <input
        type="checkbox"
        checked={todoItemData.completed}
        onChange={() => handleToggleCompletion(todoItemData.id)}
      />
      <p className="flex-1 flex items-center">{todoItemData.text}</p>
      <select
        value={todoItemData.priority}
        onChange={(e) =>
          handleUpdatePriority(todoItemData.id, e.target.value as PriorityType)
        }
      >
        <option value={"low"}>Low</option>
        <option value={"medium"}>Medium</option>
        <option value={"high"}>high</option>
      </select>
      <button
        className="btn btn-secondary"
        onClick={() => handleDeleteTodo(todoItemData.id)}
      >
        <X className="text-red-500" />
      </button>
    </div>
  );
};

function TodoList({ todoData }: TodoListProps) {
  const [todoDataState, setTodoDataState] = useState(todoData);
  const [todoText, setTodoText] = useState("");

  const handleUpdateTodoText = (newText: string) => {
    setTodoText(newText);
  };

  const handleAddTodo = () => {
    if (!todoText.trim()) return;

    // add the new todo to the existing todo
    setTodoDataState((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        text: todoText,
        completed: false,
        priority: "low",
      },
    ]);

    // clear input text of todo
    setTodoText("");
  };

  const handleToggleCompletion = (id: number | string) => {
    const todoUpdatedData = todoDataState.map((todoData) => {
      return todoData.id === id
        ? {
            ...todoData,
            completed: !todoData.completed,
          }
        : todoData;
    });

    setTodoDataState(todoUpdatedData);
  };

  const handleUpdatePriority = (
    id: string | number,
    priority: PriorityType
  ) => {
    const todoUpdatedData = todoDataState.map((todoData) => {
      return todoData.id === id
        ? {
            ...todoData,
            priority: priority,
          }
        : todoData;
    });

    setTodoDataState(todoUpdatedData);
  };

  const handleDeleteTodo = (id: string | number) => {
    const todoUpdatedData = todoDataState.filter(
      (todoData) => todoData.id !== id
    );

    if (!todoUpdatedData) return;

    setTodoDataState(todoUpdatedData);
  };

  return (
    <div className="task-container">
      <h2>Task 6: Todo List with useState</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Add new todos</li>
          <li>Delete todos</li>
          <li>Mark todos as complete</li>
        </ul>
      </div>

      <div className="implementation flex flex-col gap-3">
        {/* add new task container */}
        <div className="flex gap-4">
          <input
            value={todoText}
            placeholder="Add a new task"
            onChange={(e) => handleUpdateTodoText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleAddTodo();
              }
            }}
          />
          <button className="btn btn-primary" onClick={handleAddTodo}>
            Add
          </button>
        </div>

        {/* display todo */}
        <div className="flex flex-col gap-2">
          {todoDataState.length === 0 ? (
            <p>No Todo to display</p>
          ) : (
            todoDataState.map((todoItem) => (
              <TodoItem
                key={todoItem.id}
                todoItemData={todoItem}
                handleToggleCompletion={handleToggleCompletion}
                handleUpdatePriority={handleUpdatePriority}
                handleDeleteTodo={handleDeleteTodo}
              />
            ))
          )}
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            The component uses <code>useState</code> to manage the list of todos
            (<code>todoDataState</code>) and the current input value (
            <code>todoText</code>).
          </li>
          <li>
            Each todo item contains an <code>id</code>, <code>text</code>,{" "}
            <code>completed</code> boolean, and <code>priority</code> ("low",
            "medium", "high").
          </li>
          <li>
            Todos are rendered using the <code>TodoItem</code> child component,
            which receives props for toggling completion and updating priority.
          </li>
          <li>
            A new todo can be added via the input field and "Add" button, which
            appends a new todo to the state with default values.
          </li>
          <li>
            <code>handleToggleCompletion</code> toggles the{" "}
            <code>completed</code> status of a todo by mapping and updating the
            matched item.
          </li>
          <li>
            <code>handleUpdatePriority</code> updates the priority of a specific
            todo in state based on its <code>id</code>.
          </li>
          <li>
            The input field is controlled, with its value synced via{" "}
            <code>handleUpdateTodoText</code>.
          </li>
          <li>
            The component currently includes all CRUD functionality except for
            deletion (which is mentioned in the requirements but not implemented
            yet).
          </li>
          <li>
            Each <code>TodoItem</code> uses a checkbox for completion and a{" "}
            <code>&lt;select&gt;</code> dropdown to change priority dynamically.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default TodoList;
