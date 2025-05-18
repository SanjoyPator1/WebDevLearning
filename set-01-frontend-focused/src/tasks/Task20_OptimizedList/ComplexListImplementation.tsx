import React, { useRef, useState, useCallback } from "react";
import { VariableSizeList as List } from "react-window";

const itemCount = 500; // Fewer items since they're more complex

// Define complex item data structure
interface ComplexItem {
  id: number;
  title: string;
  description: string;
  priority: number;
  tags: string[];
  isCompleted: boolean;
  lastUpdated: Date;
  assignee?: string;
}

// Complex list item props
interface ComplexItemProps {
  index: number;
  style: React.CSSProperties;
  data: {
    items: ComplexItem[];
    measureRef: (index: number, node: HTMLElement | null) => void;
  };
}

// Complex item component
const ListItem: React.FC<ComplexItemProps> = ({ index, style, data }) => {
  const { items, measureRef } = data;
  const item = items[index];

  return (
    <div
      style={style}
      ref={(node) => measureRef(index, node)}
      className="p-4 border-b border-gray-200 hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-lg flex items-center">
          {item.title}
          <span className="ml-2 text-sm font-normal text-gray-500">
            #{item.id}
          </span>

          {item.isCompleted && (
            <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
              Completed
            </span>
          )}
        </h3>

        <div
          className={`px-2 py-1 rounded text-xs ${
            item.priority === 1
              ? "bg-red-100 text-red-800"
              : item.priority === 2
              ? "bg-yellow-100 text-yellow-800"
              : "bg-green-100 text-green-800"
          }`}
        >
          Priority: {item.priority}
        </div>
      </div>

      <p className="text-sm text-gray-700 my-2">{item.description}</p>

      <div className="flex items-center justify-between mt-3">
        <div className="flex flex-wrap gap-1">
          {item.tags.map((tag, i) => (
            <span
              key={i}
              className="bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-xs"
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="flex items-center gap-3">
          {item.assignee && (
            <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
              {item.assignee}
            </span>
          )}
          <span className="text-xs text-gray-500">
            {item.lastUpdated.toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
};

// Custom comparison function for React.memo
// Only re-render if important properties have changed
const arePropsEqual = (
  prevProps: ComplexItemProps,
  nextProps: ComplexItemProps
) => {
  // Always re-render if index changes
  if (prevProps.index !== nextProps.index) return false;

  const prevItem = prevProps.data.items[prevProps.index];
  const nextItem = nextProps.data.items[nextProps.index];

  // Skip comparison if items aren't loaded yet
  if (!prevItem || !nextItem) return false;

  // Check for important visual property changes
  if (prevItem.title !== nextItem.title) return false;
  if (prevItem.description !== nextItem.description) return false;
  if (prevItem.priority !== nextItem.priority) return false;
  if (prevItem.isCompleted !== nextItem.isCompleted) return false;
  if (prevItem.assignee !== nextItem.assignee) return false;

  // Deep compare tags (arrays)
  if (prevItem.tags.length !== nextItem.tags.length) return false;
  if (!prevItem.tags.every((tag, i) => tag === nextItem.tags[i])) return false;

  // For dates, compare timestamps
  if (prevItem.lastUpdated.getTime() !== nextItem.lastUpdated.getTime())
    return false;

  // If we got here, all important properties are equal
  return true;
};

// Use the custom comparison function with React.memo
const MemoizedListItem = React.memo(ListItem, arePropsEqual);

// Create a complex list implementation with custom memo
const ComplexListImplementation: React.FC = () => {
  const listRef = useRef<any>(null);
  const rowHeightMap = useRef<{ [key: number]: number }>({});

  // Generate complex sample data
  const [items] = useState<ComplexItem[]>(() =>
    Array.from({ length: itemCount }, (_, i) => {
      // Randomize content properties
      const priority = Math.floor(Math.random() * 3) + 1;
      const isCompleted = Math.random() > 0.7;

      // Generate random tags
      const possibleTags = [
        "bug",
        "feature",
        "ui",
        "backend",
        "frontend",
        "api",
        "database",
        "security",
        "performance",
      ];
      const numTags = Math.floor(Math.random() * 4) + 1;
      const tags: string[] = [];
      for (let j = 0; j < numTags; j++) {
        const randomTag =
          possibleTags[Math.floor(Math.random() * possibleTags.length)];
        if (!tags.includes(randomTag)) tags.push(randomTag);
      }

      // Maybe assign to someone
      const assignees = [
        "Alice",
        "Bob",
        "Charlie",
        "Diana",
        undefined,
        undefined,
      ];
      const assignee = assignees[Math.floor(Math.random() * assignees.length)];

      // Generate more text for some items
      const descriptionLength = Math.floor(Math.random() * 3);
      let description = "";
      if (descriptionLength === 0) {
        description = `Short task description for complex item ${i + 1}.`;
      } else if (descriptionLength === 1) {
        description = `This is a medium length description for complex task ${
          i + 1
        }. It contains additional details about what needs to be done.`;
      } else {
        description = `This is a detailed specification for complex task ${
          i + 1
        }. It contains multiple sentences explaining exactly what needs to be accomplished. This type of detailed description is common in project management tools. It helps team members understand the full scope of work required.`;
      }

      return {
        id: i + 1,
        title: `Complex Task ${i + 1}`,
        description,
        priority,
        tags,
        isCompleted,
        lastUpdated: new Date(
          Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000
        ),
        assignee,
      };
    })
  );

  // Calculate item height based on content
  const getItemHeight = useCallback(
    (index: number) => {
      // Return cached height if available
      if (rowHeightMap.current[index]) {
        return rowHeightMap.current[index];
      }

      // Estimate height based on content length and number of tags
      const item = items[index];
      const descriptionLength = item.description.length;
      const tagCount = item.tags.length;

      // Base height plus additional height for longer descriptions and more tags
      const estimatedHeight =
        100 +
        Math.ceil(descriptionLength / 50) * 20 +
        (tagCount > 2 ? 10 : 0) +
        (item.assignee ? 10 : 0);

      return estimatedHeight;
    },
    [items]
  );

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

export default ComplexListImplementation;
