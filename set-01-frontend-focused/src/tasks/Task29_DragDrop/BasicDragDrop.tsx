import { Minus } from 'lucide-react';
import { useState } from 'react';


// dummy data
const dummyData = ["apple", "mango", "cat", "dog", "lion", "tiger"]

const BasicDragDrop = () => {

  const [draggedItem, setDraggedItem] = useState<string | null>(null)
  const [droppedItem, setDroppedItem] = useState<string[]>([])

  // DRAG ITEM - functions
  // called when user starts dragging
  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, item: string) => {
    console.log("handle drag start : item= ", { item })

    setDraggedItem(item)
    // Set the visual effect - 'move' shows a move cursor
    e.dataTransfer.effectAllowed = "move"
    // Optional: Store data that can be retrieved on drop
    e.dataTransfer.setData("text/plain", item)

  }

  // called when user stops draggin - for cleanup
  const handleDragEnd = () => {
    console.log("handle drag end")
    setDraggedItem(null)   // Cleanup in case drop didn't happen
  }

  // DROP ZONE - functions
  // called continuously  when dragged over drop zone
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    console.log("handle drag over called")

    e.preventDefault()  // CRITICAL: Prevents default behavior to allow drop
    // Without preventDefault(), the drop event will not fire
    // Set visual feedback for the drop operation
    e.dataTransfer.effectAllowed = "move"
  }

  const handleOnDrop = (e: React.DragEvent<HTMLDivElement>) => {
    console.log("handle on drop called")
    // Prevent default handling (like opening as link)
    e.preventDefault()

    if (draggedItem) {
      // Add the dragged item to dropped items array
      setDroppedItem((prev) => [...prev, draggedItem])
      // Clear the dragged item state
      setDraggedItem(null)
    }
  }

  // handler to remove item from drop zone
  const handleRemoveItem = (indexToRemove: number) => {
    console.log("handle remove item called with index - ", { indexToRemove })
    // const newDroppedItemList = droppedItem.filter((_,index)=>  index!==indexToRemove)
    // setDroppedItem(newDroppedItemList)

    setDroppedItem((prev) => prev.filter((_, index) => index !== indexToRemove))
  }

  return (
    <div className='space-y-3'>
      <h4>Basic Drag and Drop</h4>
      <div className='grid grid-cols-2 gap-6 h-[400px] overflow-y-auto p-4 border rounded-lg bg-gray-100'>
        {/* items container */}
        <div className='border rounded-md p-4 space-y-2'>
          <label>Draggable list</label>
          {
            dummyData.map((item) => {
              return (
                <div
                  key={item}
                  // makes the element draggable
                  draggable
                  // handler for drag start
                  onDragStart={(e) => handleDragStart(e, item)}
                  // handler for drag end
                  onDragEnd={handleDragEnd}
                  className={`border rounded-md p-2 cursor-move`}
                >
                  {item}
                </div>
              )
            })
          }
        </div>

        {/* drop zone */}
        <div
          // required for dropping
          onDragOver={handleDragOver}
          // handles the actual drop event
          onDrop={handleOnDrop}
          className='border rounded-md border-dashed p-4 space-y-2'>
          <label>Drop zone</label>
          {
            droppedItem.map((item, index) => {
              return (
                <div
                  key={`${item} - ${index}`}
                  className={`border rounded-md p-2 flex justify-between items-center`}
                >
                  {item}
                  <button
                    onClick={() => handleRemoveItem(index)}
                    className='btn btn-secondary'
                  >
                    <Minus />
                  </button>
                </div>
              )
            })
          }
        </div>
      </div>
      <div className="mt-4 border-t pt-4 space-y-2">
        <h5 className="font-semibold text-lg">Notes:</h5>
        <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
          <li>
            <span className="font-medium">Draggable Items:</span> Items from the left box are made draggable using the
            <code className="bg-gray-100 px-1 rounded mx-1">draggable</code> attribute. When a drag starts,
            <code className="bg-gray-100 px-1 rounded mx-1">handleDragStart</code> stores the item being dragged and sets data transfer metadata.
          </li>
          <li>
            <span className="font-medium">Drop Zone:</span> The right container allows drop by using
            <code className="bg-gray-100 px-1 rounded mx-1">onDragOver</code> with
            <code className="bg-gray-100 px-1 rounded mx-1">e.preventDefault()</code>. This is required to make drop events functional.
          </li>
          <li>
            <span className="font-medium">Drop Action:</span> On drop, the dragged item is appended to the drop zone's state array via
            <code className="bg-gray-100 px-1 rounded mx-1">setDroppedItem</code>. The
            <code className="bg-gray-100 px-1 rounded mx-1">draggedItem</code> is then cleared.
          </li>
          <li>
            <span className="font-medium">Item Removal:</span> Each dropped item renders a delete button. On click, the item is removed using
            <code className="bg-gray-100 px-1 rounded mx-1">filter</code> based on its index. The function uses a
            <code className="bg-gray-100 px-1 rounded mx-1">prev =&gt; ...</code> pattern for safe state updates.
          </li>
          <li>
            <span className="font-medium">Unique Key Strategy:</span> Since items may have duplicates, keys use a combination of item name and index to ensure uniqueness.
          </li>
          <li>
            <span className="font-medium">Styling:</span> Layout uses Tailwind's
            <code className="bg-gray-100 px-1 rounded mx-1">grid-cols-2</code>,
            <code className="bg-gray-100 px-1 rounded mx-1">border-dashed</code>, and
            <code className="bg-gray-100 px-1 rounded mx-1">cursor-move</code> for visual cues.
          </li>
          <li>
            <span className="font-medium">Best Practices:</span> All handlers are kept clean and minimal. Using
            <code className="bg-gray-100 px-1 rounded mx-1">useCallback</code> can optimize performance if this scales.
          </li>
        </ul>
      </div>
    </div>
  );
};

export default BasicDragDrop;
