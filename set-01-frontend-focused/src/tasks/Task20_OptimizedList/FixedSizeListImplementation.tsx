import React, { useState } from "react";
import { FixedSizeList as List } from "react-window";

const itemCount = 1000;
const itemHeight = 40;

interface SimpleItem {
  id: number;
  text: string;
}

interface FixedSizeItemProps {
  index: number;
  style: React.CSSProperties; // This is critical for react-window positioning
  data: SimpleItem[];
}

// Simple list item component
const ListItem: React.FC<FixedSizeItemProps> = ({ index, style, data }) => {
  const item = data[index];

  return (
    <div
      style={style}
      className="flex items-center px-4 py-2 border-b border-gray-200 hover:bg-gray-50"
    >
      <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-blue-100 rounded-full mr-3">
        {index + 1}
      </div>
      <div className="flex-grow">
        <div className="font-medium">Item #{item.id}</div>
        <div className="text-sm text-gray-600">{item.text}</div>
      </div>
    </div>
  );
};

// Memoized list item to prevent unnecessary re-renders
const MemoizedListItem = React.memo(ListItem);

const FixedSizeListImplementation: React.FC = () => {
  const [items] = useState<SimpleItem[]>(() =>
    Array.from({ length: itemCount }, (_, i) => ({
      id: i + 1,
      text: `This is list item ${i + 1} with fixed height`,
    }))
  );

  return (
    <List
      height={384} // Container height
      itemCount={itemCount}
      itemSize={itemHeight}
      width="100%"
      itemData={items}
    >
      {(props) => <MemoizedListItem {...props} data={items} />}
    </List>
  );
};

export default FixedSizeListImplementation;

// NOTE: The style prop from react-window contains absolute positioning information that places each item at the correct position in the virtual list. Without applying this style, items would stack on top of each other or be positioned incorrectly.
