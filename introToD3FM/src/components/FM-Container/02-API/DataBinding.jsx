import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

function DataBinding() {
  const elRef = useRef(null);
  const [data, setData] = useState([45, 67, 96, 84, 41]);

  useEffect(() => {
    const svg = d3.select(elRef.current);

    const rects = svg.selectAll("rect").data(data);

    // console.log("select datum ", svg.select("rect").datum(data));
    // console.log("selectAll datum ", svg.selectAll("rect").datum(data));
    // console.log("selectAll data ", svg.selectAll("rect").data(data));

    rects.exit().remove();
  }, [data]);

  return (
    <div>
      Won't display anything <br /> - by choice
      <svg ref={elRef} width={150} height={100}>
        <rect />
        <rect />
        <rect />
        <rect />
        <rect />
      </svg>
    </div>
  );
}

export default DataBinding;
