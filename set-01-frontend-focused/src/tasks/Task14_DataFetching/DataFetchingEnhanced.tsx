import { useState } from "react";
import { USER_DATA, type UserType } from "../../shared/utils/tasksData";
import type { ApiReturnMode } from "./useSimulatedFetch";
import useSimulatedFetch from "./useSimulatedFetch";

const DELAY_FETCHING = 1000

const fetchUsersApi = (mode: ApiReturnMode):UserType[]  => {
  if (mode === "error") {
    throw new Error("Error while fetching users! SORRY :)");
  }
  return  USER_DATA ;
};

function DataFetchingSimulationEnhanced() {
  const [fetchMode, setFetchMode] = useState<ApiReturnMode>("success");

  const {data,loading,error} = useSimulatedFetch({fetchMode, delay:DELAY_FETCHING,fn:fetchUsersApi})

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
            data && Array.isArray(data) && data.length>0 && data.map((user) => (
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
          <li>Use `setTimeout` to simulate a network request</li>
          <li>Use `useState` to manage loading, success, and error states</li>
        </ul>
      </div>
    </div>
  );
}

export default DataFetchingSimulationEnhanced;
