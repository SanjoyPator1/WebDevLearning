import { useEffect, useState } from "react";
import useDebounce from "./useDebounce";

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

function DebouncedSearchEnhanced() {
  const [searchInput, setSearchInput] = useState("");
  const [searchedUsers, setSearchedUsers] = useState<UserType[]>([]);

  const debounceSearch = useDebounce(searchInput, 500);

  useEffect(() => {
    if (!debounceSearch.trim()) {
      setSearchedUsers([]);
      return;
    }
    const results = findUserByName(debounceSearch);
    setSearchedUsers(results);
  }, [debounceSearch]);

  return (
    <div className="task-container">
      <h2>Task 12.2: Enhanced Debounced Search</h2>

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
          <p>Debounced search text: {debounceSearch}</p>
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
            <strong>Debouncing logic:</strong> Implemented using{" "}
            <code>setTimeout</code> inside a <code>useEffect</code> hook to
            delay updates by 500ms.
          </li>
          <li>
            <strong>Cleanup:</strong> <code>clearTimeout</code> is used in the
            cleanup function to avoid overlapping timers when the input changes
            quickly.
          </li>
          <li>
            <strong>Search triggering:</strong> Another <code>useEffect</code>{" "}
            watches the debounced input and only triggers the search if the
            input is non-empty.
          </li>
          <li>
            <strong>Search logic:</strong> The <code>findUserByName</code>{" "}
            function simulates an API call using local <code>USER_DATA</code>{" "}
            and performs a case-insensitive search using <code>includes</code>.
          </li>
          <li>
            <strong>Rendering:</strong> Search results and the full user list
            are displayed in separate sections. Each item uses a unique{" "}
            <code>key</code> (user ID) to avoid React key warnings.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default DebouncedSearchEnhanced;

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
