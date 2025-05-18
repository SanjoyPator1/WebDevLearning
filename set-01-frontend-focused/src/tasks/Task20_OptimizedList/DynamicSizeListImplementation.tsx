import React, { useRef, useState, useCallback } from "react";
import { VariableSizeList as List } from "react-window";

const itemCount = 1000;

interface VariableItem {
  id: number;
  title: string;
  content: string;
}

interface DynamicSizeItemProps {
  index: number;
  style: React.CSSProperties;
  data: {
    items: VariableItem[];
    measureRef: (index: number, node: HTMLElement | null) => void;
  };
}

const ListItem: React.FC<DynamicSizeItemProps> = ({ index, style, data }) => {
  const { items, measureRef } = data;
  const item = items[index];
  
  return (
    <div 
      style={style} 
      ref={node => measureRef(index, node)}
      className="px-4 py-3 border-b border-gray-200 hover:bg-gray-50"
    >
      <h3 className="font-medium text-gray-800">{item.title}</h3>
      <p className="text-sm text-gray-600 mt-1">{item.content}</p>
    </div>
  );
};

const MemoizedListItem = React.memo(ListItem);

const DynamicSizeListImplementation: React.FC = () => {
  const listRef = useRef<any>(null);
  const rowHeightMap = useRef<{[key: number]: number}>({});
  
  const [items] = useState<VariableItem[]>(() => 
    Array.from({ length: itemCount }, (_, i) => {
      // Create different content lengths to demonstrate variable heights
      const contentLength = Math.floor(Math.random() * 3);
      
      let content = '';
      if (contentLength === 0) {
        content = `Short description for item ${i + 1}.`;
      } else if (contentLength === 1) {
        content = `This is a medium length description for item ${i + 1}. It has a bit more text to show how variable height works.`;
      } else {
        content = `This is a much longer description for item ${i + 1}. It contains multiple sentences to demonstrate how the list handles items with significantly more content. The height of this item will be much taller than others, and the virtualized list should handle this correctly. This helps show how dynamic sizing works.`;
      }
      
      return {
        id: i + 1,
        title: `Variable Item ${i + 1}`,
        content
      };
    })
  );

  // Estimate item height based on content
  const getItemHeight = useCallback((index: number) => {
    // Return cached height if available
    if (rowHeightMap.current[index]) {
      return rowHeightMap.current[index];
    }
    
    // Estimate based on content length
    const contentLength = items[index].content.length;
    const estimatedHeight = 60 + Math.ceil(contentLength / 40) * 20;
    
    return estimatedHeight;
  }, [items]);
  
  // Measure and store actual item height
  const measureRef = useCallback((index: number, node: HTMLElement | null) => {
    if (node) {
      const height = node.getBoundingClientRect().height;
      
      // Only update if height changed significantly
      if (Math.abs(height - (rowHeightMap.current[index] || 0)) > 2) {
        rowHeightMap.current[index] = height;
        
        // Tell list to recompute
        if (listRef.current) {
          listRef.current.resetAfterIndex(index);
        }
      }
    }
  }, []);

  return (
    <List
      ref={listRef}
      height={384} // Container height
      itemCount={itemCount}
      itemSize={getItemHeight}
      width="100%"
      itemData={{ items, measureRef }}
    >
      {MemoizedListItem}
    </List>
  );
};

export default DynamicSizeListImplementation;