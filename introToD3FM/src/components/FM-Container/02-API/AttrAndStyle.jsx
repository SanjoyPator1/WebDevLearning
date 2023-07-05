import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

const AttrAndStyle = () => {
  const barData = [45, 67, 96, 84, 41];

  const elRef = useRef(null);
  const rectWidth = 50;

  useEffect(() => {
    const svg = d3.select(elRef.current);

    svg
      .selectAll("rect")
      .data(barData)
      // calculate x-position based on its index
      .attr("x", (d, i) => i * rectWidth)
      // calculate y-position based on its index
      .attr("y", (d, i) => 100 - d)

      // set height based on the bound datum
      .attr("height", (d) => d)

      // rest of attributes are constant values
      .attr("width", rectWidth)
      .attr("stroke-width", 3)
      .attr("stroke-dasharray", "5 5")
      .attr("stroke", "plum")
      .attr("fill", "pink");
  }, [barData]);

  return (
    <svg
      ref={elRef}
      width={rectWidth * barData.length}
      height={100}
      style={{ border: "1px dashed" }}
    >
      <rect />
      <rect />
      <rect />
      <rect />
      <rect />
    </svg>
  );
};

export default AttrAndStyle;
