import React, { useState } from 'react';

const initialItems = ['Item 1', 'Item 2', 'Item 3', 'Item 4'];

const SortableList: React.FC = () => {

  const [itemList, setItemList] = useState<string[]>(initialItems)
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)

  const handleDragStart = (draggedItemIndex: number) => {
    setDraggedIndex(draggedItemIndex)
  }

  const handleDragEnd = () => {
    setDraggedIndex(null)
  }

  const handleDragOver = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault()
  }

  const handleDrop = (targetIndex: number) => {
    if (draggedIndex === null || draggedIndex === targetIndex) return

    const newItemList = [...itemList];
    [newItemList[draggedIndex], newItemList[targetIndex]] = [newItemList[targetIndex], newItemList[draggedIndex]]

    setItemList(newItemList)
    setDraggedIndex(null)
  }

  return (
    <div className='space-y-3'>
      <h4 className="text-lg font-semibold mb-4">Sortable List</h4>
      <div className="p-4 border rounded-lg bg-gray-100">

        <ul className='space-y-2'>
          {
            itemList.map((item, index) => {
              return (
                <li
                  key={`${item}-${index}`}
                  draggable
                  onDragStart={() => handleDragStart(index)}
                  onDragEnd={handleDragEnd}
                  onDragOver={handleDragOver}
                  onDrop={() => handleDrop(index)}
                  className={`p-2 bg-white cursor-move border hover:border-blue-500 rounded-md transition-opacity ${draggedIndex === index ? 'opacity-50' : 'opacity-100'
                    }`}               >
                  {item}
                </li>
              )
            })
          }
        </ul>

      </div>

      <div className="mt-4 border-t pt-4 space-y-2">
        <h5 className="font-semibold text-lg">Notes:</h5>
        <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
          <li>
            <span className="font-medium">Sortable Items:</span> Each list item is made draggable using the
            <code className="bg-gray-100 px-1 rounded mx-1">draggable</code> attribute. When dragging starts,
            <code className="bg-gray-100 px-1 rounded mx-1">handleDragStart</code> stores the dragged item's index in state for later reference.
          </li>
          <li>
            <span className="font-medium">Drag Over Handling:</span> Each item acts as both draggable and drop target using
            <code className="bg-gray-100 px-1 rounded mx-1">onDragOver</code> with
            <code className="bg-gray-100 px-1 rounded mx-1">e.preventDefault()</code>. This is essential to enable the drop functionality on list items.
          </li>
          <li>
            <span className="font-medium">Swap Logic:</span> On drop, items are reordered using array destructuring swap:
            <code className="bg-gray-100 px-1 rounded mx-1">[array[i], array[j]] = [array[j], array[i]]</code>. This simple approach swaps the dragged item with the drop target.
          </li>
          <li>
            <span className="font-medium">State Management:</span> The component uses
            <code className="bg-gray-100 px-1 rounded mx-1">draggedIndex</code> to track which item is being dragged and
            <code className="bg-gray-100 px-1 rounded mx-1">itemList</code> for the current order. State is reset after successful drops.
          </li>
          <li>
            <span className="font-medium">Drag End Cleanup:</span> The
            <code className="bg-gray-100 px-1 rounded mx-1">onDragEnd</code> handler ensures
            <code className="bg-gray-100 px-1 rounded mx-1">draggedIndex</code> is cleared even if the drop fails, preventing stuck drag states.
          </li>
          <li>
            <span className="font-medium">Visual Feedback:</span> Items being dragged receive
            <code className="bg-gray-100 px-1 rounded mx-1">opacity-50</code> styling to provide clear visual feedback during the drag operation.
          </li>
          <li>
            <span className="font-medium">Guard Conditions:</span> The drop handler includes safety checks:
            <code className="bg-gray-100 px-1 rounded mx-1">draggedIndex === null</code> and
            <code className="bg-gray-100 px-1 rounded mx-1">draggedIndex === targetIndex</code> to prevent invalid operations.
          </li>
          <li>
            <span className="font-medium">React Keys:</span> List items use
            <code className="bg-gray-100 px-1 rounded mx-1">{"key={`${item}-${index}`}"}</code> to ensure React can track items correctly during reordering operations.
          </li>
          <li>
            <span className="font-medium">TypeScript Types:</span> Uses proper typing with
            <code className="bg-gray-100 px-1 rounded mx-1">React.DragEvent&lt;HTMLLIElement&gt;</code> for drag events and
            <code className="bg-gray-100 px-1 rounded mx-1">number | null</code> for the dragged index state.
          </li>
          <li>
            <span className="font-medium">Performance:</span> The swap approach is O(1) complexity, making it efficient for lists of any size. For larger lists, consider adding
            <code className="bg-gray-100 px-1 rounded mx-1">useCallback</code> to memoize event handlers.
          </li>
        </ul>
      </div>

    </div>
  );
};

export default SortableList;
