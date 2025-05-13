import { useState } from "react";
import Select from "./Select";

function CompoundComponentPattern() {
  const [selectedValue, setSelectedValue] = useState<string | null>(null);

  const handleChange = (value: string) => {
    setSelectedValue(value);
  };

  return (
    <div className="task-container">
      <h2>Task 16: Compound Component Pattern</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a custom select component using compound components</li>
          <li>Clicking the select opens a dropdown</li>
          <li>Selecting an option updates the parent value</li>
          <li>Close the dropdown when clicking outside</li>
        </ul>
      </div>

      <div className="implementation">
        <div className="md:w-[500px]">
          <Select value={selectedValue} onChange={handleChange}>
            <Select.Trigger>
              {selectedValue
                ? `Selected : ${selectedValue}`
                : "Select an option"}
            </Select.Trigger>
            <Select.Dropdown>
              <Select.Option value={"apple"}>Apple</Select.Option>
              <Select.Option value={"mango"}>Mango</Select.Option>
              <Select.Option value={"banana"}>Banana</Select.Option>
              <Select.Option value={"strawberry"}>Strawberry</Select.Option>
            </Select.Dropdown>
          </Select>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            Used the compound component pattern with React Context to create a
            flexible, reusable select component.
          </li>
          <li>
            Implemented the main <code>Select</code> component that manages
            state and provides context to child components.
          </li>
          <li>
            Created three subcomponents: <code>Trigger</code> (the button that
            opens the dropdown), <code>Dropdown</code> (container for options),
            and <code>Option</code> (individual selectable items).
          </li>
          <li>
            Used <code>useCallback</code> for event handlers to optimize
            performance and prevent unnecessary re-renders.
          </li>
          <li>
            Implemented outside click detection using <code>useEffect</code> and
            a ref to close the dropdown when clicking elsewhere.
          </li>
          <li>
            Added proper accessibility attributes including ARIA roles and
            states for screen reader support.
          </li>
          <li>
            Used Lucide icons (<code>ArrowUp</code>, <code>ArrowDown</code>,{" "}
            <code>Check</code>) for visual indicators.
          </li>
          <li>
            Made the component fully typed with TypeScript for better developer
            experience and error prevention.
          </li>
          <li>
            Styled the component with Tailwind CSS, using conditional classes
            based on component state.
          </li>
          <li>
            Created the component as controlled (parent manages state) through
            value and onChange props.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default CompoundComponentPattern;
