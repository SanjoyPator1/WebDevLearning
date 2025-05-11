import { useState } from "react";

interface IChildCounterProps {
  title: string;
  value: number;
  onChange: (delta: number) => void;
}

const ChildCounter: React.FC<IChildCounterProps> = ({
  title,
  value,
  onChange,
}) => {
  return (
    <div className="rounded-md bg-blue-200 p-2 flex justify-between">
      <div>
        <h4>{title}</h4>
        <div className="flex gap-2">
          <label>Counter</label>: <p>{value}</p>
        </div>
      </div>
      <div className="flex gap-2">
        <button className="btn btn-primary" onClick={() => onChange(1)}>
          +
        </button>
        <button className="btn btn-primary" onClick={() => onChange(-1)}>
          -
        </button>
      </div>
    </div>
  );
};

function ParentChild() {
  const [childCounts, setChildCounts] = useState([0, 0, 0]);

  const handleChildChange = (index: number, delta: number) => {
    const updatedCounts = [...childCounts];
    updatedCounts[index] += delta;
    setChildCounts(updatedCounts);
  };

  const handleReset = () => {
    setChildCounts([0, 0, 0]);
  };

  const totalCount = childCounts.reduce((sum, val) => sum + val, 0);

  return (
    <div className="task-container">
      <h2>Task 9: Parent-Child Communication</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Parent displays total from all child counters</li>
          <li>Each child can increment/decrement its own value</li>
          <li>Parent has button to reset all counters</li>
        </ul>
      </div>

      <div className="implementation flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <label>Total</label>
          <p className="text-3xl">{totalCount}</p>
        </div>

        {/* Child counters */}
        <div className="flex flex-col gap-2">
          {childCounts.map((count, index) => (
            <ChildCounter
              key={index}
              title={`Counter 0${index + 1}`}
              value={count}
              onChange={(delta) => handleChildChange(index, delta)}
            />
          ))}
        </div>

        <button className="w-fit btn btn-primary" onClick={handleReset}>
          Reset All Counters
        </button>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul className="list-disc list-inside space-y-1">
          <li>
            <strong>State is lifted to the parent component:</strong> Each
            child's counter value is controlled by the parent (`ParentChild`
            component). This follows the React principle of "lifting state up",
            which is essential when multiple components need to share or
            coordinate the same state.
          </li>
          <li>
            <strong>Child components are made reusable and controlled:</strong>{" "}
            The `ChildCounter` receives its current value and an `onChange`
            callback as props from the parent. This makes each child a
            presentational (or "dumb") component — it doesn't manage its own
            state but instead informs the parent of changes.
          </li>
          <li>
            <strong>Total is computed dynamically:</strong> The total counter
            value is calculated using `reduce` on the `childCounts` array. This
            ensures that the total is always up to date with the actual child
            values and avoids the risk of desynchronization between total and
            individual counters.
          </li>
          <li>
            <strong>Reset button clears all child counters:</strong> Clicking
            the reset button sets all child values to `0` by updating the entire
            `childCounts` array. Because the parent manages state, this reset
            action affects all children immediately.
          </li>
          <li>
            <strong>Why manage state in the parent?</strong> When multiple child
            components influence shared data (like the total count), it's best
            practice in React to centralize the state in the parent. This avoids
            bugs, keeps data in sync, and allows better control over component
            behavior.
          </li>
          <li>
            <strong>Communication flow:</strong> Children use the
            `onChange(delta)` callback to inform the parent of changes
            (increment/decrement). The parent updates the corresponding state
            and re-renders both the total and the specific child.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default ParentChild;
