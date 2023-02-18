// ScalesImplementation

import React, { useRef, useState, useEffect } from "react";
import * as d3 from "d3";
import _ from "lodash";

const ScalesImplementation = () => {
  const [bars, setBars] = useState(7);
  const [width, setWidth] = useState(window.innerWidth - 600);
  const [height, setHeight] = useState(375);
  const [padding, setPadding] = useState(0.5);

  const data = _.times(bars, (i) => _.random(0, 100));
  // console.log("data sp ", data);

  const xScale = d3
    .scaleBand()
    .domain(d3.range(data.length))
    .range([0, width])
    .padding(padding);

  const max = d3.max(data, (d) => d);

  const yScale = d3
    .scaleLinear()
    .domain([0, max + 20])
    .range([height, 0]);

  const svgRef = useRef();

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg
      .selectAll("rect")
      .data(data)
      .join("rect")
      .attr("x", (_, i) => xScale(i))
      .attr("y", (d) => yScale(d))
      .attr("width", xScale.bandwidth())
      .attr("height", (d) => height - yScale(d))
      .attr("stroke-width", 3)
      .attr("stroke", "plum")
      .attr("fill", "pink");

    svg
      .selectAll("text.x-coordinate")
      .data(data)
      .join("text")
      .attr("class", "x-coordinate")
      .attr("x", (_, i) => xScale(i) + xScale.bandwidth() / 2)
      .attr("y", (d) => yScale(d) - 20)
      .text((d, i) => `X: ${xScale(i).toFixed(2)}`)
      .style("text-anchor", "middle")
      .style("font-family", "monospace")
      .style("font-size", ".75em");

    svg
      .selectAll("text.y-coordinate")
      .data(data)
      .join("text")
      .attr("class", "y-coordinate")
      .attr("x", (_, i) => xScale(i) + xScale.bandwidth() / 2)
      .attr("y", (d) => yScale(d) - 6)
      .text((d) => `Y: ${yScale(d).toFixed(2)}`)
      .style("text-anchor", "middle")
      .style("font-family", "monospace")
      .style("font-size", ".75em");
  }, [data, xScale, yScale, height]);

  return (
    <div style={{ padding: "40px", width: "95%" }}>
      <svg ref={svgRef} width={width} height={height} />
      <div style={{ backgroundColor: "black", padding: "0.6em" }}>
        <div>
          <label>Number of bars:</label>
          <input
            type="range"
            min={1}
            max={30}
            value={bars}
            onChange={(e) => setBars(e.target.value)}
          />
          <span>{bars}</span>
        </div>
        <div>
          <label>Width:</label>
          <input
            type="range"
            min={100}
            max={window.innerWidth - 100}
            value={width}
            onChange={(e) => setWidth(e.target.value)}
          />
          <span>{width}</span>
        </div>
        <div>
          <label>Height:</label>
          <input
            type="range"
            min={50}
            max={500}
            value={height}
            onChange={(e) => setHeight(e.target.value)}
          />
          <span>{height}</span>
        </div>
        <div>
          <label>Padding:</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={padding}
            onChange={(e) => setPadding(e.target.value)}
          />
          <span>{padding}</span>
        </div>
      </div>
    </div>
  );
};

export default ScalesImplementation;
