import { useEffect, useState } from "react";
import { USER_DATA, type UserType } from "../../shared/utils/tasksData";

type ApiReturnMode = "success" | "error";

type ApiReturnType = {
  data: UserType[];
};

const fetchUsersApi = (returnType: ApiReturnMode): ApiReturnType => {
  if (returnType === "error") {
    throw new Error("Error while fetching users! SORRY :)");
  }
  return { data: USER_DATA };
};

const simulateFetch = (mode: ApiReturnMode): Promise<ApiReturnType> => {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      try {
        const response = fetchUsersApi(mode);
        resolve(response);
      } catch (err) {
        reject(err);
      }
    }, 2000);
  });
};

function DataFetchingSimulation() {
  const [fetchedUsers, setFetchedUsers] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchMode, setFetchMode] = useState<ApiReturnMode>("success");

  useEffect(() => {
    setLoading(true);
    setError(null);

    simulateFetch(fetchMode)
      .then((res) => setFetchedUsers(res.data))
      .catch((e) => {
        const error = e as Error;
        setError(error.message);
      })
      .finally(() => setLoading(false));

    return () => {
    };
  }, [fetchMode]);

  return (
    <div className="task-container">
      <h2>Task 14: Data Fetching Simulation</h2>

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
            fetchedUsers.map((user) => (
              <div key={user.id} className="flex border rounded-md p-3">
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

export default DataFetchingSimulation;
