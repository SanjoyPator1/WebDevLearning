import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { movies,colors } from "../../../data";

const AttrAndStyleGenreExercise = () => {
  const elRef = useRef(null);

  const petalPath =
    "M0,0 C50,40 50,70 20,100 L0,85 L-20,100 C-50,70 -50,40 0,0";

  useEffect(() => {
    const svg = d3.select(elRef.current);

    // console.log("movies ", movies);
    svg
      .selectAll("path")
      .data(movies)
      .attr("fill", (d) => colors[d.genres[0]] || colors.Other)
      .attr("fill-opacity", 0.5)
      .attr("stroke", (d) => colors[d.genres[0]] || colors.Other);
  }, [movies]);

  return (
    <div>
      <svg
        ref={elRef}
        width={500}
        height={100}
        style={{ border: "1px dashed" }}
      >
        <path d={petalPath} transform="translate(50, 0)" />
        <path d={petalPath} transform="translate(150, 0)" />
        <path d={petalPath} transform="translate(250, 0)" />
        <path d={petalPath} transform="translate(350, 0)" />
        <path d={petalPath} transform="translate(450, 0)" />
      </svg>
    </div>
  );
};

export default AttrAndStyleGenreExercise;
