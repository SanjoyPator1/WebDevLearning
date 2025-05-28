import BasicDragDrop from "./BasicDragDrop";
import SortableList from "./SortableList";

function DragAndDropSorting() {
  return (
    <div className="task-container">
      <h2>Task 29: Drag and Drop Sorting</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a list that supports drag-and-drop sorting</li>
          <li>Update the order of items based on user interaction</li>
        </ul>
      </div>

      <div className="space-y-6">
        <BasicDragDrop/>
        <SortableList/>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>Use the HTML5 Drag and Drop API</li>
          <li>Update the list order in state after sorting</li>
        </ul>
      </div>
    </div>
  );
}

export default DragAndDropSorting;
