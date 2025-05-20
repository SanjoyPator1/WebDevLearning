import React, { Suspense, useState, type JSX } from "react";

const HomeLazy = React.lazy(()=>import("./HomeLazy"))
const AboutLazy = React.lazy(()=>import("./AboutLazy"))
const DashboardLazy = React.lazy(()=>import("./DashboardLazy"))

export const tabs = ["home", "about", "dashboard"] as const;
export type TabsType = typeof tabs[number];

// simple switch to render tab content
// const renderTab = (tab: TabsType) =>{
//   switch(tab){
//     case "home":
//       return <HomeLazy/>
//     case "about":
//       return <AboutLazy/>
//     case "dashboard":
//       return <DashboardLazy/>
//     default:
//       return <p>Default page lol</p>
//   }
// }

// use improved lazy component map for scalability and readability
const lazyComponentMap: Record<TabsType, React.LazyExoticComponent<() => JSX.Element>> = {
  home: HomeLazy,
  about: AboutLazy,
  dashboard: DashboardLazy
}

const renderTab = (tab: TabsType) =>{
  const Component = lazyComponentMap[tab]

  return <Component/>
}

function ReactLazyAndCodeSplitting() {
  const [activeTab, setActiveTab] = useState<TabsType>("home")

  return (
    <div className="task-container">
      <h2>Task 23: React.lazy and Code Splitting</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create multiple page components</li>
          <li>Use `React.lazy` to load them dynamically</li>
          <li>Add `Suspense` with a fallback loader</li>
        </ul>
      </div>

      <div className="implementation">
        <div className="flex gap-2">
          {tabs.map((tab)=>{
            return(
              <button
                key={tab}
                className={`btn ${tab===activeTab ? "btn-primary":"btn-secondary"}`}
                onClick={()=>setActiveTab(tab)}
              >
                {tab}
              </button>
            )
          })}
        </div>
        <div>
          <Suspense fallback={<div className="text-blue-500 h-[100px] flex items-center justify-center w-fit">Loading component...</div>}>
            {renderTab(activeTab)}
          </Suspense>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Used <code>React.lazy</code> to dynamically import components, reducing the initial bundle size and improving performance.</li>
          <li>Implemented a <code>lazyComponentMap</code> using a <code>Record&lt;TabsType, React.LazyExoticComponent&lt;...&gt;&gt;</code> for cleaner and scalable tab rendering logic.</li>
          <li>Wrapped dynamic content inside <code>Suspense</code> with a fallback UI to handle loading states gracefully.</li>
          <li>Used a strongly typed <code>TabsType</code> union from a <code>const</code> array to ensure tab safety and prevent invalid tab states.</li>
          <li>Added <code>key</code> prop to each rendered tab button to avoid React reconciliation issues.</li>
        </ul>
      </div>
    </div>
  );
}

export default ReactLazyAndCodeSplitting;
