import React from "react";
import "./TaskRenderer.css";

import Toggle from "../../tasks/Task02_Toggle/Toggle";
import TextExpander from "../../tasks/Task03_TextExpander/TextExpander";
import Accordion from "../../tasks/Task04_Accordion/Accordion";
import Tabs from "../../tasks/Task05_Tabs/Tabs";
import TodoList from "../../tasks/Task06_TodoList/TodoList";
import TrafficLight from "../../tasks/Task07_TrafficLight/TrafficLight";
import FormInputs from "../../tasks/Task08_FormInputs/FormInputs";
import ParentChild from "../../tasks/Task09_ParentChild/ParentChild";
import ShoppingCart from "../../tasks/Task10_ShoppingCart/ShoppingCart";
import Counter from "../../tasks/Task01_Counter/Counter";
import { AccordionMockData, longText } from "../../shared/utils/tasksData";

interface TaskRendererProps {
  currentTask: string | null;
}

const TaskRenderer: React.FC<TaskRendererProps> = ({ currentTask }) => {
  const taskComponents: Record<string, React.ReactNode> = {
    counter: <Counter />,
    toggle: <Toggle />,
    textExpander: <TextExpander text={longText} />,
    accordion: <Accordion accordionData={AccordionMockData}/>,
    tabs: <Tabs />,
    todoList: <TodoList />,
    trafficLight: <TrafficLight />,
    formInputs: <FormInputs />,
    parentChild: <ParentChild />,
    shoppingCart: <ShoppingCart />,
  };

  if (currentTask && taskComponents[currentTask]) {
    return <div className="task-component">{taskComponents[currentTask]}</div>;
  }

  return (
    <div className="welcome">
      <h2>React Interview Practice Tasks</h2>
      <p>Select a task from the list to see the implementation.</p>
      <p className="hint">
        Start with basic components and work your way up to more advanced
        patterns.
      </p>
    </div>
  );
};

export default TaskRenderer;
