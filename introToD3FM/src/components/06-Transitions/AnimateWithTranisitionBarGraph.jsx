import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import _ from "lodash";
import { useState } from "react";

const AnimateWithTranisitionBarGraph = () => {
  let barData = [45, 20, 67, 96, 84, 41];
  const [dataToShow, setdataToShow] = useState(barData);

  const elRef = useRef(null);
  const rectWidth = 50;
  const svgHeight = 150;

  const createBarGraph = () => {
    // select svg so that transition can be localized within selection
    const t = d3.select(elRef.current).transition().duration(1000);

    // Generate an array of 10 random numbers between 1 and 100
    const randomNumbers = _.times(4, () => _.random(10, 100));
    randomNumbers.push(84);
    randomNumbers.push(45);
    barData = randomNumbers;
    setdataToShow(randomNumbers);

    d3.select(elRef.current)
      .selectAll("rect")
      .data(barData, (d) => d)
      .join(
        (enter) => {
          return (
            enter
              .append("rect")
              //attributes to transition FROM
              .attr("x", (d, i) => i * rectWidth)
              .attr("height", 0)
              .attr("y", svgHeight)
              .attr("stroke-width", 3)
              .attr("stroke", "plum")
              .attr("fill", "pink")
          ); //y position to be bottom of the SVG i.e 150 since coordinate starts grom top(0) to botton(150){i.e svgHeight}
        },
        (update) => update,
        (exit) => {
          exit
            .transition(t)
            // everything after here is transition TO
            .attr("height", 0)
            .attr("y", svgHeight);
        }
      ) //enter + update selection
      .attr("width", rectWidth) //before transition since we don't want to animate
      .transition(t)
      //attributes to tranistion to
      .attr("x", (d, i) => i * rectWidth)
      .attr("height", (d) => d)
      .attr("y", (d) => svgHeight - d);

    // //selection
    // const rect = d3
    //   .select(elRef.current)
    //   .selectAll("rect")
    //   .data(barData, (d) => d);

    // //exit
    // rect.exit().remove();

    // //enter
    // const enter = rect
    //   .enter()
    //   .append("rect")
    //   .attr("width", rectWidth)
    //   .attr("stroke-width", 3)
    //   .attr("stroke", "plum")
    //   .attr("fill", "pink");

    // //enter + update
    // enter
    //   .merge(rect)
    //   // calculate x-position based on its index
    //   .attr("x", (d, i) => i * rectWidth)
    //   // calculate y-position based on its index
    //   .attr("y", (d, i) => 100 - d)
    //   // set height based on the bound datum
    //   .attr("height", (d) => d);
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
        style={{ border: "1px dashed", margin: "10px" }}
      ></svg>
      <button onClick={createBarGraph}>Change Data</button>
      <div
        style={{
          backgroundColor: "black",
          height: "40px",
          display: "flex",
          alignItems: "center",
          margin: "5px",
          padding: "5px",
        }}
      >
        Data =
        {dataToShow.map((item) => {
          {
            // console.log("item sp ", item);
          }
          return <p style={{ color: "white", marginInline: "5px" }}>{item}</p>;
        })}
      </div>
    </div>
  );
};

export default AnimateWithTranisitionBarGraph;
