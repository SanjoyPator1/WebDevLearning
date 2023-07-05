import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import _ from "lodash";
import { useState } from "react";
import { Button } from "@mui/material";

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
  };

  useEffect(() => {
    createBarGraph();
  }, []);

  return (
    <div>
      <div
        style={{ margin: "0 auto", width: "fit-content", marginBlock: "0.5em" }}
      >
        <svg ref={elRef} width={rectWidth * barData.length} height={150}></svg>
      </div>
      <Button
        style={{ marginBlock: "0.5em" }}
        variant="contained"
        onClick={createBarGraph}
      >
        Change Data
      </Button>
      <div
        style={{
          backgroundColor: "#A084DC",
          height: "40px",
          display: "flex",
          alignItems: "center",
          margin: "5px",
          padding: "10px",
        }}
      >
        <label style={{ color: "white" }}>Data =</label>
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
