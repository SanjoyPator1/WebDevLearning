import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import _ from "lodash";

const EnterUpdateOldWay = () => {
  let barData = [45, 67, 96, 84, 41];
  const [dataToShow, setDataToShow] = useState(barData);

  const elRef = useRef(null);
  const rectWidth = 50;

  const createBarGraph = () => {
    // Generate an array of 10 random numbers between 1 and 100
    const randomNumbers = _.times(3, () => _.random(10, 100));
    randomNumbers.push(84);
    randomNumbers.push(45);
    barData = randomNumbers;
    setDataToShow(barData);
    //selection
    const rect = d3
      .select(elRef.current)
      .selectAll("rect")
      .data(barData, (d) => d);

    // console.log("enter-update old way rect ", rect);
    //exit
    rect.exit().remove();
    // console.log("enter-update old way rect after exit ", rect);

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

    // console.log("enter-update old way enter after update ", rect);
  };

  useEffect(() => {
    createBarGraph();
  }, []);

  return (
    <div>
      <div style={{ color: "black" }}>Old Way</div>
      <svg
        ref={elRef}
        width={rectWidth * barData.length}
        height={150}
        style={{ border: "1px dashed" }}
      ></svg>
      <button onClick={createBarGraph}>Change Data</button>
      <div
        style={{
          backgroundColor: "black",
          height: "30px",
          width: "70%",
          display: "flex",
          padding: "10px",
          margin: "0.3em",
        }}
      >
        Data =
        {dataToShow.map((item) => {
          {
            // console.log("item sp ", item);
          }
          return (
            <div style={{ color: "white", marginInline: "5px" }}> {item}</div>
          );
        })}
      </div>
    </div>
  );
};

export default EnterUpdateOldWay;
