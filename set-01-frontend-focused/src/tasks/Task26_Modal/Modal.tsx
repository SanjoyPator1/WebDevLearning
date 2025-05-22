import { useState } from "react";
import ModalSimple from "./ModalSimple";
import ModalPortal from "./ModalPortal";
import ModalAdvancedPortal from "./ModalAdvancedPortal";

function ModalDialog() {

  const [isSimpleModalOpen, setSimpleModalOpen] = useState(false)
  const [isModalPortalOpen, setModalPortalOpen] = useState(false)
  const [isModalAdvancedPortalOpen, setModalAdvancedPortalOpen] = useState(false)

  return (
    <div className="task-container">
      <h2>Task 26: Modal Dialog</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a modal dialog component</li>
          <li>Include open and close functionality</li>
          <li>Overlay should close the modal when clicked</li>
          <li>Support keyboard accessibility (e.g., Escape key to close)</li>
        </ul>
      </div>

      <div className="implementation space-4">
        <div className="p-2 space-y-3">
          <label>Simple modal with overlay</label>
          <button
            className="btn btn-primary"
            onClick={() => setSimpleModalOpen(true)}
          >Open Simple modal</button>
          <ModalSimple
            title="Simple modal"
            isOpen={isSimpleModalOpen}
            onClose={() => setSimpleModalOpen(false)}
          >
            <p>This is a simple modal example with overlay</p>
          </ModalSimple>
        </div>

        <div className="p-2 space-y-3">
          <label>Modal portal with overlay</label>
          <button
            className="btn btn-primary"
            onClick={() => setModalPortalOpen(true)}
          >Open modal portal</button>
          <ModalPortal
            title="Modal portal"
            isOpen={isModalPortalOpen}
            onClose={() => setModalPortalOpen(false)}
          >
            <p>This is a modal portal with div in main root</p>
          </ModalPortal>
        </div>

        <div className="p-2 space-y-3">
          <label>Modal advanced portal with overlay</label>
          <button
            className="btn btn-primary"
            onClick={() => setModalAdvancedPortalOpen(true)}
          >Open modal advanced portal</button>
          <ModalAdvancedPortal
            title="Modal advanced portal"
            isOpen={isModalAdvancedPortalOpen}
            onClose={() => setModalAdvancedPortalOpen(false)}
          >
            <p>This is an advanced modal portal with programmatic addition of root div in body</p>
          </ModalAdvancedPortal>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul className="list-disc list-inside space-y-2">
          <li>
            <strong>useState for modal visibility:</strong>
            Modal open/close state is controlled using the <code>useState</code> hook in the parent component. This allows fine-grained control over which modal is visible and when. It also enables parent components to manage multiple modals independently.
          </li>

          <li>
            <strong>Escape key to close modal:</strong>
            We added a <code>keydown</code> event listener when the modal opens to listen for the <code>Escape</code> key. Pressing it will trigger the <code>onClose</code> handler, improving keyboard accessibility. The listener is removed during cleanup to prevent memory leaks.
          </li>

          <li>
            <strong>Overlay click to close modal:</strong>
            Clicking on the semi-transparent background (overlay) triggers the <code>onClose</code> function. However, clicks on the modal content itself are stopped from bubbling using <code>e.stopPropagation()</code>, ensuring that users can interact with the modal without accidentally closing it.
          </li>

          <li>
            <strong>Accessible modal structure:</strong>
            The modal includes <code>role="dialog"</code> and <code>aria-modal="true"</code> attributes, which help screen readers interpret the dialog correctly. If a title is provided, it's linked via <code>aria-labelledby</code> to provide context.
          </li>

          <li>
            <strong>Three modal strategies:</strong>
            This task demonstrates three ways to render modals:
            <ul className="list-disc list-inside pl-4">
              <li><strong>Simple modal:</strong> Rendered inline, useful for small apps where DOM layering isn’t an issue.</li>
              <li><strong>Modal using portal with static root:</strong> Uses a predefined <code>&lt;div id="modal-root"&gt;</code> to render outside the normal DOM hierarchy. Better for z-index and accessibility.</li>
              <li><strong>Modal using dynamic portal:</strong> Programmatically creates a portal container, improving modularity and reusability (like how libraries such as Radix UI or shadcn/ui do).</li>
            </ul>
          </li>

          <li>
            <strong>React Portals:</strong>
            Portals are used to render the modal outside the main app’s DOM tree, ensuring proper z-index stacking, focus trapping, and scroll isolation — especially useful for complex UI layers.
          </li>

          <li>
            <strong>Cleanup and memory safety:</strong>
            All <code>useEffect</code> hooks include proper cleanup to prevent memory leaks and ensure event listeners or DOM nodes are removed when the modal unmounts.
          </li>
        </ul>
      </div>

    </div>
  );
}

export default ModalDialog;
