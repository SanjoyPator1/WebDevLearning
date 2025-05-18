import React from "react";

type ListItemProps = {
  index: number;
};

const ListItem: React.FC<ListItemProps> = ({ index }) => {
  return <div className="w-full border bg-blue-200">ListItem #{index}</div>;
};

const MemoizedListItem = React.memo(ListItem);

export default MemoizedListItem;
