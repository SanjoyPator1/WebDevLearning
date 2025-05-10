import { useEffect, useState } from "react";

type TextExpanderProps = {
  text: string;
  charLimit?: number;
};

function TextExpander({ text, charLimit = 100 }: TextExpanderProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentText, setCurrentText] = useState("");

  const toggleExpand = () => {
    setIsExpanded((prev) => !prev);
  };

  useEffect(() => {
    if (isExpanded) {
      setCurrentText(text);
    } else {
      setCurrentText(
        text && text.length > charLimit
          ? text.slice(0, charLimit) + "..."
          : text
      );
    }
  }, [isExpanded, text, charLimit]);

  return (
    <div className="task-container">
      <h2>Task 3: Text Expander</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Show truncated text with "Read More" button</li>
          <li>Clicking expands to show full text with "Read Less" button</li>
          <li>Make the character limit configurable via props</li>
        </ul>
      </div>

      <div className="implementation md:w-[50vw] flex flex-col gap-3">
        <p>{currentText}</p>
        {text && text.length > charLimit && (
          <button className="w-fit" onClick={toggleExpand}>
            {isExpanded ? "Read Less" : "Read More"}
          </button>
        )}
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Character limit is passed as a prop with a default value</li>
          <li>Toggle logic handled with a boolean state</li>
          <li>useEffect updates text display on toggle or prop change</li>
        </ul>
      </div>
    </div>
  );
}

export default TextExpander;
