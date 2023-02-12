import React, { useRef, useEffect, useState } from "react";
import * as d3 from "d3";

const TranslateTransform = () => {
  const svgRef = useRef();

  //box mover
  const svgRefBox = useRef();
  const [x, setX] = useState(0);
  const [y, setY] = useState(0);

  useEffect(() => {
    const svgBox = d3.select(svgRefBox.current);

    svgBox.select("rect").attr("transform", `translate(${x}, ${y})`);
  }, [x, y]);

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    // Define the x and y scales
    const xScale = d3.scaleLinear().domain([0, 8]).range([0, 800]);

    const yScale = d3.scaleLinear().domain([0, 8]).range([0, 800]);

    // Draw the grid lines
    svg
      .selectAll(".x-line")
      .data(xScale.ticks(9))
      .enter()
      .append("line")
      .attr("class", "x-line")
      .attr("x1", (d) => xScale(d))
      .attr("y1", 0)
      .attr("x2", (d) => xScale(d))
      .attr("y2", 800);

    svg
      .selectAll(".y-line")
      .data(yScale.ticks(9))
      .enter()
      .append("line")
      .attr("class", "y-line")
      .attr("x1", 0)
      .attr("y1", (d) => yScale(d))
      .attr("x2", 800)
      .attr("y2", (d) => yScale(d));

    // Draw the squares
    svg
      .selectAll(".square")
      .data(d3.range(64))
      .enter()
      .append("rect")
      .attr("class", "square")
      .attr("x", (d, i) => xScale(i % 8))
      .attr("y", (d, i) => yScale(Math.floor(i / 8)))
      .attr("width", 100)
      .attr("height", 100)
      .attr("fill", "none")
      .attr("stroke", "#526FAD")
      .attr("stroke-width", 0.5)
      .style("stroke-dasharray", "5, 5");

    // Draw the outline
    svg
      .append("rect")
      .attr("x", 0)
      .attr("y", 0)
      .attr("width", 800)
      .attr("height", 800)
      .attr("stroke", "#526FAD")
      .attr("stroke-width", 4)
      .attr("fill", "none");
  }, []);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          position: "relative",
          width: "800px",
          height: "800px",
          backgroundColor: "white",
        }}
      >
        <svg ref={svgRef} width={800} height={800} />
        <svg
          ref={svgRefBox}
          style={{ position: "absolute", top: 0, left: 0 }}
          width={800}
          height={800}
        >
          <rect x={0} y={0} width={100} height={100} fill="#526FAD" />
        </svg>
      </div>

      <div
        style={{
          // backgroundColor: "pink",
          display: "flex",
          flexDirection: "row",
          justifyContent: "center",
          // marginTop: "10px",
          alignItems: "center",
          height: "200px",
          width: "100%",
        }}
      >
        <div
          style={{
            // display: "flex",
            // flexDirection: "row",
            // backgroundColor: "blue",
            // height: "100%",
            // alignItems: "center",
            // justifyContent: "center",
            display: "flex",
            // justifyContent: "flex-end",
            flexDirection: "row",
            width: "100px",
            height: "100%",
            // backgroundColor: "blue",
          }}
        >
          <label
            htmlFor="y-axis"
            style={{
              fontWeight: "600",
              fontSize: "20px",
              color: "#526FAD",
              // transform: "rotate(-90deg)",
              // backgroundColor: "green",
              margin: "0",
              padding: "0",
              // width: "200px",
              // height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "right",
              // fontWeight: "600",
              // fontSize: "20px",
              // color: "#526FAD",
              // margin: "0",
              // padding: "0",
            }}
          >
            Y Axis:
          </label>
          <input
            type="range"
            id="y-axis"
            min={0}
            max={700}
            value={y}
            onChange={(e) => setY(e.target.value)}
            style={{
              transform: "rotate(-270deg)",
              width: "200px",
              backgroundColor: "red",
            }}
          />
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "flex-start",
            flexDirection: "column",
            width: "200px",
            height: "100%",
            marginLeft: "125px",
            marginTop: "15px",
            // backgroundColor: "red",
          }}
        >
          <label
            htmlFor="x-axis"
            style={{
              fontWeight: "600",
              fontSize: "20px",
              color: "#526FAD",
              margin: "0",
              padding: "0",
            }}
          >
            X Axis:
          </label>
          <input
            type="range"
            id="x-axis"
            min={0}
            max={700}
            value={x}
            onChange={(e) => setX(e.target.value)}
          />
        </div>
      </div>

      <div
        style={{ display: "flex", justifyContent: "center", marginTop: "10px" }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            marginRight: "20px",
          }}
        >
          <label
            htmlFor="x-axis"
            style={{ fontWeight: "700", fontSize: "30px", color: "#526FAD" }}
          >{`transform='translate(${x}, ${y})'`}</label>
        </div>
      </div>
    </div>
  );
};

export default TranslateTransform;
