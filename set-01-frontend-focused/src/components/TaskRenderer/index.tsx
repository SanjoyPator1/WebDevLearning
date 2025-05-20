import React from "react";
import "./TaskRenderer.css";

import Counter from "../../tasks/Task01_Counter/Counter";
import Toggle from "../../tasks/Task02_Toggle/Toggle";
import TextExpander from "../../tasks/Task03_TextExpander/TextExpander";
import Accordion from "../../tasks/Task04_Accordion/Accordion";
import Tabs from "../../tasks/Task05_Tabs/Tabs";
import TodoList from "../../tasks/Task06_TodoList/TodoList";
import TrafficLight from "../../tasks/Task07_TrafficLight/TrafficLight";
import FormInputs from "../../tasks/Task08_FormInputs/FormInputs";
import ParentChild from "../../tasks/Task09_ParentChild/ParentChild";
import ShoppingCart from "../../tasks/Task10_ShoppingCart/ShoppingCart";
import Timer from "../../tasks/Task11_Timer/Timer";
import DebouncedSearchEnhanced from "../../tasks/Task12_DebouncedSearch/DebouncedSearchEnhanced";
import WindowSizeTracker from "../../tasks/Task13_WindowSizeTracker/WindowSizeTracker";
import {
  AccordionMockData,
  longText,
  TabData,
  todoDummyData,
} from "../../shared/utils/tasksData";
import DataFetchingSimulation from "../../tasks/Task14_DataFetching/DataFetching";
import DebouncedSearch from "../../tasks/Task12_DebouncedSearch/DebouncedSearch";
import DataFetchingSimulationEnhanced from "../../tasks/Task14_DataFetching/DataFetchingEnhanced";
import CustomUseFetchHook from "../../tasks/Task15_CustomFetchHook/CustomFetchHook";
import CompoundComponentPattern from "../../tasks/Task16_CompoundComponent/CompoundComponent";
import RenderPropsPattern from "../../tasks/Task17_RenderProps/RenderProps";
import HigherOrderComponents from "../../tasks/Task18_HOC/HOC";
import CustomHookWithLocalStorage from "../../tasks/Task19_LocalStorageHook/LocalStorageHook";
import OptimizedListRendering from "../../tasks/Task20_OptimizedList/OptimizedList";
import MemoizationPractice from "../../tasks/Task21_Memoization/Memoization";
import UseCallbackImplementation from "../../tasks/Task22_UseCallback/UseCallback";

// Welcome component with Tailwind CSS
const Welcome = () => (
  <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center p-6">
    <div className="max-w-md">
      <h2 className="text-2xl font-bold mb-4 text-gray-900">
        React Interview Practice Tasks
      </h2>
      <p className="text-gray-600 mb-3">
        Select a task from the list to see the implementation.
      </p>
      <p className="text-sm text-gray-500 italic mt-6">
        Start with basic components and work your way up to more advanced
        patterns.
      </p>
    </div>
  </div>
);

interface TaskRendererProps {
  currentTask: string | null;
}

const TaskRenderer: React.FC<TaskRendererProps> = ({ currentTask }) => {
  // Map of task IDs to their respective components
  const taskComponents: Record<string, React.ReactNode> = {
    welcome: <Welcome />,
    counter: <Counter />,
    toggle: <Toggle />,
    textExpander: <TextExpander text={longText} />,
    accordion: <Accordion accordionData={AccordionMockData} />,
    tabs: <Tabs tabData={TabData} />,
    todoList: <TodoList todoData={todoDummyData} />,
    trafficLight: <TrafficLight />,
    formInputs: <FormInputs />,
    parentChild: <ParentChild />,
    shoppingCart: <ShoppingCart />,
    timer: <Timer />,
    debouncedSearch: <DebouncedSearch />,
    debouncedSearchEnhanced: <DebouncedSearchEnhanced />,
    windowSizeTracker: <WindowSizeTracker />,
    dataFetching: <DataFetchingSimulation />,
    dataFetchingEnhanced: <DataFetchingSimulationEnhanced />,
    customFetchHook: <CustomUseFetchHook />,
    compoundComponent: <CompoundComponentPattern />,
    renderProps: <RenderPropsPattern />,
    hoc: <HigherOrderComponents />,
    localStorageHook: <CustomHookWithLocalStorage />,
    optimizedList: <OptimizedListRendering />,
    memoization: <MemoizationPractice />,
    useCallback: <UseCallbackImplementation/>
    // Add more task components as you implement them
  };

  // If no task is selected (null), show the welcome page
  if (!currentTask) {
    return (
      <div className="task-component">
        <Welcome />
      </div>
    );
  }

  // If the task is selected but not in our components map
  if (!taskComponents[currentTask]) {
    // This should never happen with our current setup since App.tsx handles the validation
    // But we'll include it for safety in case the component is used elsewhere
    return (
      <div className="task-component">
        <div className="flex flex-col items-center justify-center h-full text-center p-6">
          <div className="max-w-md">
            <h2 className="text-2xl font-bold mb-4 text-red-600">
              Task Component Missing
            </h2>
            <p className="text-gray-600 mb-3">
              The task "{currentTask}" exists but its component hasn't been
              implemented yet.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Return the selected task component
  return <div className="task-component">{taskComponents[currentTask]}</div>;
};

export default TaskRenderer;
