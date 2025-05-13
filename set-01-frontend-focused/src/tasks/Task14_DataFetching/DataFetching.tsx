import { useEffect, useState } from "react";
import { USER_DATA, type UserType } from "../../shared/utils/tasksData";

const DELAY_FETCHING = 1000

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
    }, DELAY_FETCHING);
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
      <h2>Task 14.1: Data Fetching Simulation</h2>

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
            A simulated fetch function (<code>simulateFetch</code>) is used to mimic an asynchronous API call. It introduces a delay using <code>setTimeout</code> and either resolves with mock user data or throws an error based on the selected mode ("success" or "error").
          </li>
          <li>
            <code>useEffect</code> runs every time the <code>fetchMode</code> state changes. It triggers the data fetch process, resets error/loading states, and updates the component state with either the fetched data or the error message.
          </li>
          <li>
            Three key state variables are used: <code>fetchedUsers</code> to store retrieved users, <code>loading</code> to indicate loading status, and <code>error</code> to hold any error message from a failed fetch.
          </li>
          <li>
            A toggle switch (checkbox) allows switching between "success" and "error" fetch modes to test both flows. The label displays the current mode.
          </li>
          <li>
            The UI conditionally renders content: a loading message during fetch, an error message if fetching fails, or a list of users if data is fetched successfully.
          </li>
          <li>
            Type safety is ensured using TypeScript types: <code>UserType</code> for user objects, and <code>ApiReturnMode</code> and <code>ApiReturnType</code> for API response handling.
          </li>
        </ul>
      </div>

    </div>
  );
}

export default DataFetchingSimulation;
