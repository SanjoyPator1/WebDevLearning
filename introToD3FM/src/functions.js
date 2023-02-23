const perRow = 7;
const pathWidth = 120;

export const calculateGridPos = (i) => {
  const row = Math.floor(i / perRow);
  const x = (i % perRow) * pathWidth;
  const y = row * pathWidth;
  return [x, y];
};
