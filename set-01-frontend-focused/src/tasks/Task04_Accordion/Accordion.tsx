import { ChevronDown, ChevronUp } from "lucide-react";
import type React from "react";
import { useState } from "react";

export type AccordionItemType = {
  id: string;
  title: string;
  content: string;
};

export type AccordionProps = {
  accordionData: AccordionItemType[];
};

const AccordionItem: React.FC<AccordionItemType> = ({ id, title, content }) => {
  const [open, setOpen] = useState(false);

  const handleToggleOpen = () => {
    setOpen((prev) => !prev);
  };

  return (
    <div className={`border rounded-md px-4 py-2 ${open && "my-4"}`}>
      <button
        onClick={handleToggleOpen}
        className="w-full flex justify-between cursor-pointer"
      >
        {title}
        {open ? <ChevronUp /> : <ChevronDown />}
      </button>
      {open && <div className="">{content}</div>}
    </div>
  );
};

function Accordion({ accordionData }: AccordionProps) {
  return (
    <div className="task-container">
      <h2>Task 4: Accordion Component</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Display a list of items with titles</li>
          <li>Clicking a title shows/hides its content</li>
          <li>Use mock data for items</li>
        </ul>
      </div>

      <div className="implementation">
        {accordionData.map((accordionItem) => (
          <AccordionItem
            key={accordionItem.id}
            id={accordionItem.id}
            title={accordionItem.title}
            content={accordionItem.content}
          />
        ))}
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            Each accordion item is rendered using the <code>AccordionItem</code>{" "}
            component, which manages its own open/close state using{" "}
            <code>useState</code>.
          </li>
          <li>
            Clicking on the button toggles the open state, which conditionally
            renders the content and changes the chevron icon.
          </li>
          <li>
            ChevronUp and ChevronDown icons are imported from{" "}
            <code>lucide-react</code> to visually indicate open or closed state.
          </li>
          <li>
            The <code>Accordion</code> component maps over mock data (
            <code>accordionData</code>) and renders each item.
          </li>
          <li>
            The <code>AccordionItemType</code> type ensures that each item has
            an <code>id</code>, <code>title</code>, and <code>content</code> for
            consistent data structure.
          </li>
          <li>
            Basic Tailwind CSS classes are used for styling the layout, spacing,
            and borders of the accordion items.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Accordion;
