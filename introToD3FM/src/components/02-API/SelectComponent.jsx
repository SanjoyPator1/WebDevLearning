import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

const SelectComponent = () => {
  const svgContainerRef = useRef(null);

  useEffect(() => {
    // wrap SVG element with d3
    const svgRec = d3.select(svgContainerRef.current);

    // select the first path in the svg selection
    // (note: selections can be chained)
    const selectRec = svgRec.select("rect");

    // select all the paths in the svg selection
    const selectAllRec = svgRec.selectAll("rect");

    // console.log("svgRef ", svgContainerRef);
    // console.log("select Rec ", selectRec);
    // console.log("selectAll Rec ", selectAllRec);
  }, []);

  return (
    <div>
      <svg ref={svgContainerRef}>
        <rect x={25} y={25} width={50} height={50} fill="red" />
        <rect x={75} y={75} width={50} height={50} fill="yellow" />
        <rect x={25} y={75} width={50} height={50} fill="blue" />
        <rect x={75} y={25} width={50} height={50} fill="green" />
      </svg>
    </div>
  );
};

export default SelectComponent;
