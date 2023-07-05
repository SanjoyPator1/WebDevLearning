import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { movies, pathObj,colors } from "../../../data";

// const movies = movieData.splice(0, 500);

const CreateDomElementsExercise = () => {
  // console.log("movies coming out", movies);

  const pathWidth = 120;
  const [width, setWidth] = useState(window.innerWidth);
  const [perRow, setPerRow] = useState(Math.floor(width / pathWidth));
  const [svgHeight, setSvgHeight] = useState(
    (Math.ceil(movies.length / perRow) + 0.5) * pathWidth
  );

  const calculateGridPos = (i) => {
    const x = ((i % perRow) + 0.5) * pathWidth;
    const y = (Math.floor(i / perRow) + 0.5) * pathWidth;
    // console.log(`trans pos x= ${x} & y=${y}`);
    return [x, y];
  };

  const elRef = useRef(null);

  useEffect(() => {
    // console.log("movies coming in", movies);
    setWidth(window.innerWidth);
    setPerRow(Math.floor(width / pathWidth));
    setSvgHeight((Math.ceil(movies.length / perRow) + 0.5) * pathWidth);

    const svg = d3.select(elRef.current);
    svg
      .selectAll("path")
      .data(movies)
      .enter()
      .append("path")
      .attr("transform", (d, i) => `translate(${calculateGridPos(i)})`)
      .attr("d", (d) => pathObj[d?.rated])
      .attr("fill", (d) => colors[d.genres[0]] || colors.Other)
      .attr("fill-opacity", 0.5)
      .attr("stroke", (d) => colors[d.genres[0]] || colors.Other);
  }, [movies]);

  return (
    <div>
      <svg
        ref={elRef}
        width={width}
        height={svgHeight}
        style={{ border: "1px dashed" }}
      ></svg>
    </div>
  );
};

export default CreateDomElementsExercise;
