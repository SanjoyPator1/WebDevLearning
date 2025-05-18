import HoverCardRenderProps from "./HoverCardRenderpropsPattern";

const FirstRender = (isHovered: boolean) => (
  <div className={`w-full border rounded-md p-3 transition ${isHovered ? "bg-blue-300" : "bg-gray-100"}`}>
    FirstRender Special text shown on hover - isHovered - {isHovered.toString()}
  </div>
);


const SecondRender = (isHovered: boolean) => {
  return (
    <div className={`w-full border rounded-md p-3 transition ${isHovered ? "bg-blue-300" : "bg-gray-100"}`}>
      SecondRender Special text shown on hover - isHovered - {isHovered.toString()}
    </div>
  )
}

function RenderPropsPattern() {
  return (
    <div className="task-container">
      <h2>Task 17: Render Props Pattern</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a `HoverCard` component that accepts render props</li>
          <li>Detect mouse hover over an element</li>
          <li>Show additional content on hover</li>
        </ul>
      </div>

      <div className="implementation flex flex-col gap-4">
        <HoverCardRenderProps
          render={FirstRender}
        />

        <HoverCardRenderProps
          render={SecondRender}
        />
      </div>

      <div className="task-notes mt-6 p-4 border rounded-lg bg-gray-50">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Implementation Notes:</h3>
        <ul className="list-disc list-inside space-y-1 text-gray-700">
          <li>
            The <code>HoverCardRenderProps</code> component uses the <strong>render props pattern</strong> to expose the <code>isHovered</code> state to its children.
          </li>
          <li>
            We attach <code>mouseenter</code> and <code>mouseleave</code> events directly to the DOM node using a <code>ref</code> to ensure scoped hover detection.
          </li>
          <li>
            The render function passed as a prop returns custom content that conditionally renders based on the hover state.
          </li>
          <li>
            Tailwind CSS is used for styling and transitions to keep the UI clean and responsive.
          </li>
          <li>
            The hover state is managed internally with <code>useState</code> and <code>useEffect</code>, and properly cleaned up to avoid memory leaks.
          </li>
        </ul>
      </div>

    </div>
  );
}

export default RenderPropsPattern;
