import { useState } from "react";
import { USER_DATA, type UserType } from "../../shared/utils/tasksData";
import type { ApiReturnMode } from "./useSimulatedFetch";
import useSimulatedFetch from "./useSimulatedFetch";

const DELAY_FETCHING = 1000

const fetchUsersApi = (mode: ApiReturnMode): UserType[] => {
  if (mode === "error") {
    throw new Error("Error while fetching users! SORRY :)");
  }
  return USER_DATA;
};

function DataFetchingSimulationEnhanced() {
  const [fetchMode, setFetchMode] = useState<ApiReturnMode>("success");

  const { data, loading, error } = useSimulatedFetch({ fetchMode, delay: DELAY_FETCHING, fn: fetchUsersApi })

  return (
    <div className="task-container">
      <h2>Task 14.2: Enhanced Data Fetching Simulation</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Simulate data fetching with an artificial delay</li>
          <li>Show a loading state while fetching</li>
          <li>Handle success and error states</li>
        </ul>
      </div>

      <div className="implementation">
        <h4>Fetched User List</h4>
        <div className="flex gap-2">
          <label>Fetch mode success/error: </label>
          <p>{fetchMode}</p>
          <input
            type="checkbox"
            checked={fetchMode === "success"}
            onChange={() =>
              setFetchMode((prev) => (prev === "success" ? "error" : "success"))
            }
          />
        </div>

        <div className="space-y-3 md:h-[300px] overflow-y-auto">
          {loading ? (
            <p>Loading...</p>
          ) : error ? (
            <p>Error: {error}</p>
          ) : (
            data && Array.isArray(data) && data.length > 0 && data.map((user) => (
              <div key={user.id} className="flex gap-3 border rounded-md p-3">
                <p>{user.name}</p>
                <p>{user.avatar}</p>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            A custom hook <code>useSimulatedFetch</code> is created to abstract the logic for data fetching, managing loading and error states internally. This improves code reusability and keeps the main component clean and focused.
          </li>
          <li>
            The custom hook accepts three parameters via an object: <code>fetchMode</code> (to control success or error), <code>delay</code> (to simulate network latency), and <code>fn</code> (the actual fetch function).
          </li>
          <li>
            Inside the hook, <code>useEffect</code> handles the lifecycle of the fetch operation whenever dependencies change. It triggers the simulated fetch with a delay and updates state based on the result or error.
          </li>
          <li>
            The hook uses a generic type <code>&lt;T&gt;</code> to allow type-safe fetching of any data type, not just users. It returns an object with <code>data</code>, <code>loading</code>, and <code>error</code> values.
          </li>
          <li>
            The main component uses the hook and destructures the response state. The UI conditionally renders based on loading/error/data states and includes a checkbox to toggle between success and error modes.
          </li>
          <li>
            This approach promotes separation of concerns: the data-fetching logic lives inside the hook, while the component handles rendering and user interactions, making the code more maintainable and testable.
          </li>
        </ul>
      </div>

    </div>
  );
}

export default DataFetchingSimulationEnhanced;
