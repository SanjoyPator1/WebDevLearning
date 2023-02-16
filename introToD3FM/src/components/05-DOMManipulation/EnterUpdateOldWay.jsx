import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import _ from "lodash";

const EnterUpdateOldWay = () => {
  let barData = [45, 67, 96, 84, 41];

  const elRef = useRef(null);
  const rectWidth = 50;

  const createBarGraph = () => {
    // Generate an array of 10 random numbers between 1 and 100
    const randomNumbers = _.times(4, () => _.random(10, 100));
    randomNumbers.push(84);
    randomNumbers.push(45);
    barData = randomNumbers;
    //selection
    const rect = d3
      .select(elRef.current)
      .selectAll("rect")
      .data(barData, (d) => d);

    //exit
    rect.exit().remove();

    //enter
    const enter = rect
      .enter()
      .append("rect")
      .attr("width", rectWidth)
      .attr("stroke-width", 3)
      .attr("stroke", "plum")
      .attr("fill", "pink");

    //enter + update
    enter
      .merge(rect)
      // calculate x-position based on its index
      .attr("x", (d, i) => i * rectWidth)
      // calculate y-position based on its index
      .attr("y", (d, i) => 100 - d)
      // set height based on the bound datum
      .attr("height", (d) => d);
  };

  useEffect(() => {
    createBarGraph();
  }, []);

  return (
    <div>
      <svg
        ref={elRef}
        width={rectWidth * barData.length}
        height={150}
        style={{ border: "1px dashed" }}
      ></svg>
      <button onClick={createBarGraph}>Change Data</button>
      <h6>Data = </h6>
      <div style={{ backgroundColor: "black", height: "30px" }}>
        {barData.map((item) => {
          {
            // console.log("item sp ", item);
          }
          <h6 style={{ color: "white" }}>data {item}</h6>;
        })}
      </div>
    </div>
  );
};

export default EnterUpdateOldWay;
