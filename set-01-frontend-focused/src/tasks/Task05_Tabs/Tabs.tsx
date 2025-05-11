import { useState } from "react";

export type TabItemType = {
  id: string;
  tabTitle: string;
  tabContent: React.ReactNode;
};

export type TabsProps = {
  tabData: TabItemType[];
};

function Tabs({ tabData }: TabsProps) {
  // early return if invalid or empty data
  if (!tabData && !Array.isArray(tabData)) return null;

  const [activeTabId, setActiveTabId] = useState(
    tabData ? tabData[0].id : null
  );

  const handleSetActiveTab = (id: string) => {
    setActiveTabId(id);
  };

  const activeTab = tabData.find((tab) => tab.id === activeTabId);

  return (
    <div className="task-container">
      <h2>Task 5: Tabs Component</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Display multiple tabs with different content</li>
          <li>Only one tab content visible at a time</li>
          <li>Use mock data for tab content</li>
        </ul>
      </div>

      <div className="implementation">
        {/* Tab headers */}
        <div className="flex gap-2 border py-2 px-4 rounded-md overflow-x-auto">
          {tabData.map((tabItem) => (
            <button
              className={`btn ${
                activeTabId === tabItem.id ? "btn-primary" : "btn-secondary"
              }`}
              onClick={() => handleSetActiveTab(tabItem.id)}
            >
              {tabItem.tabTitle}
            </button>
          ))}
        </div>

        {/* Active tab content */}
        <div className="mt-4" role="tabpanel">
          {activeTab?.tabContent}
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            The <code>Tabs</code> component receives an array of tab items via
            the <code>tabData</code> prop, each containing an <code>id</code>,{" "}
            <code>tabTitle</code>, and <code>tabContent</code>.
          </li>
          <li>
            The component uses the <code>useState</code> hook to track the
            currently active tab by its <code>id</code>.
          </li>
          <li>
            Tab headers are rendered as buttons. Clicking a tab sets it as the
            active tab, and its corresponding content is displayed.
          </li>
          <li>
            Only one tab's content is visible at a time, controlled by the{" "}
            <code>activeTabId</code> state and retrieved using{" "}
            <code>Array.find</code>.
          </li>
          <li>
            Tailwind CSS classes like <code>btn</code>, <code>btn-primary</code>
            , and <code>btn-secondary</code> are used to visually distinguish
            the active tab.
          </li>
          <li>
            An early return prevents rendering if <code>tabData</code> is
            missing or not an array, adding a layer of defensive programming.
          </li>
          <li>
            The component assumes that at least one tab exists and initializes{" "}
            <code>activeTabId</code> with the first tab’s <code>id</code>.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Tabs;
