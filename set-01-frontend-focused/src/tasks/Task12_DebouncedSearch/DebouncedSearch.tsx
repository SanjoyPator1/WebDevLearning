import { useEffect, useState } from "react";

type UserType = {
  id: number;
  name: string;
  avatar: string;
};

const findUserByName = (name: string) => {
  if (!name.trim()) return [];
  console.log("simulation user find api hit");
  const userFound = USER_DATA.filter((user) =>
    user.name.toLowerCase().includes(name.toLowerCase())
  );
  return userFound;
};

function DebouncedSearch() {
  const [searchInput, setSearchInput] = useState("");
  const [searchDebouncedInput, setSearchDebouncedInput] = useState("");
  const [searchedUsers, setSearchedUsers] = useState<UserType[]>([]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebouncedInput(searchInput);
    }, 500);

    return () => {
      clearTimeout(timer);
    };
  }, [searchInput]);

  useEffect(() => {
    if (!searchDebouncedInput.trim()) {
      setSearchedUsers([]);
      return;
    }
    const results = findUserByName(searchDebouncedInput);
    setSearchedUsers(results);
  }, [searchDebouncedInput]);

  return (
    <div className="task-container">
      <h2>Task 12.1: Debounced Search</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a search input with debounced functionality</li>
          <li>Perform search only after user stops typing for 500ms</li>
          <li>Use mock data for search results</li>
        </ul>
      </div>

      <div className="implementation flex flex-col md:flex-row gap-5 justify-between">
        {/* left container showing search input and result */}
        <div className="space-y-3">
          <h4>Search users here</h4>
          <input
            placeholder="search users by name..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <p>Debounced search text: {searchDebouncedInput}</p>
          <div className="flex flex-col gap-3">
            {searchedUsers.length === 0 ? (
              <p>No Users to show</p>
            ) : (
              searchedUsers.map((userItem) => {
                return (
                  <div key={userItem.id} className="flex gap-2 justify-between">
                    {userItem.name}
                    {userItem.avatar}
                  </div>
                );
              })
            )}
          </div>
        </div>
        {/* right container showing all the users */}
        <div className="space-y-4">
          <h4>All users</h4>
          <div className="space-y-3 px-3 md:h-[500px] overflow-y-scroll">
            {USER_DATA.map((userItem) => {
              return (
                <div key={userItem.id} className="flex gap-2 justify-between">
                  {userItem.name}
                  {userItem.avatar}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            <strong>Debouncing logic</strong> is implemented using{" "}
            <code>setTimeout</code> inside a <code>useEffect</code>, which waits
            500ms before updating the debounced input state.
          </li>
          <li>
            A cleanup function is provided using <code>clearTimeout</code> to
            prevent multiple timer executions on rapid input changes.
          </li>
          <li>
            A second <code>useEffect</code> watches the debounced input and only
            performs a search if the input is not empty, ensuring performance
            optimization and clean UX.
          </li>
          <li>
            <code>findUserByName</code> is a mock function that simulates an API
            call using local <code>USER_DATA</code> and case-insensitive search
            with <code>includes</code> instead of exact match.
          </li>
          <li>
            The search results and full user list are displayed in separate
            sections for clarity, and each user item has a unique
            <code>key</code> based on <code>user.id</code> to prevent React key
            warnings.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default DebouncedSearch;

const USER_DATA: UserType[] = [
  { id: 0, name: "Sanjoy", avatar: "🤓" },
  { id: 1, name: "Aisha", avatar: "😎" },
  { id: 2, name: "Liam", avatar: "🧠" },
  { id: 3, name: "Zara", avatar: "🧚" },
  { id: 4, name: "Noah", avatar: "🧙" },
  { id: 5, name: "Maya", avatar: "🧝" },
  { id: 6, name: "Ethan", avatar: "👨‍💻" },
  { id: 7, name: "Aria", avatar: "👩‍🚀" },
  { id: 8, name: "Leo", avatar: "🦁" },
  { id: 9, name: "Nina", avatar: "🐱" },
  { id: 10, name: "Omar", avatar: "🐼" },
  { id: 11, name: "Chloe", avatar: "🦄" },
  { id: 12, name: "Aiden", avatar: "🐉" },
  { id: 13, name: "Layla", avatar: "🧞" },
  { id: 14, name: "Kai", avatar: "🐺" },
  { id: 15, name: "Mila", avatar: "🦋" },
  { id: 16, name: "Jasper", avatar: "🦊" },
  { id: 17, name: "Sofia", avatar: "🐰" },
  { id: 18, name: "Ravi", avatar: "🐯" },
  { id: 19, name: "Yuki", avatar: "🐧" },
];
