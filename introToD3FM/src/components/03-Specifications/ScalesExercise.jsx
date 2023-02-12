import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import {
  colorObj,
  movies,
  pathObj,
  petalColors,
  petalPaths,
  topGenres,
} from "../../data";
import { colors } from "../../data";

// const movies = movieData.splice(0, 500);

const ScalesExercise = () => {
  const pathWidth = 120;
  const [width, setWidth] = useState(window.innerWidth);
  const [perRow, setPerRow] = useState(Math.floor(width / pathWidth));
  const [svgHeight, setSvgHeight] = useState(
    (Math.ceil(movies.length / perRow) + 0.5) * pathWidth
  );

  const [flowers, setFlowers] = useState([]);

  const calculateGridPos = (i) => {
    const x = ((i % perRow) + 0.5) * pathWidth;
    const y = (Math.floor(i / perRow) + 0.5) * pathWidth;
    // console.log(`trans pos x= ${x} & y=${y}`);
    return [x, y];
  };

  const elRef = useRef(null);

  //initial flower data setup from movies
  useEffect(() => {
    // movie genre → `color` (color of petals)
    // array of top genres: `topGenres`
    // array of colors to map to: `petalColors`
    const colorScale = d3
      .scaleOrdinal()
      .domain(topGenres)
      .range(petalColors)
      .unknown(colorObj.Other);

    // `rated` → `path` (type of flower petal)
    // array to map to: `petalPaths`
    const pathScale = d3.scaleOrdinal().range(petalPaths);

    // `rating` → `scale` (size of petals)
    const minMaxRating = d3.extent(movies, (d) => d.rating);
    const sizeScale = d3.scaleLinear().domain(minMaxRating).range([0.2, 0.75]);

    // `votes` → `numPetals` (number of petals)
    const minMaxVotes = d3.extent(movies, (d) => d.votes);
    const numPetalScale = d3
      .scaleQuantize()
      .domain(minMaxVotes)
      .range([5, 6, 7, 8, 9, 10]);

    console.log("topGenres", topGenres);
    console.log("petalColors", petalColors);
    console.log("colorObj", colorObj);
    console.log("petalPaths", petalPaths);

    setFlowers(
      movies.map((d, i) => ({
        color: colorScale(d.genres[0]),
        path: pathScale(d.rated),
        scale: sizeScale(d.rating),
        numPetals: numPetalScale(d.votes),
        title: d.title,
        translate: calculateGridPos(i),
      }))
    );
  }, [movies]);

  //after flower data is set
  useEffect(() => {
    console.log("flowers data", flowers);

    //magic with svg
    // console.log("movies sp", movies);
    setWidth(window.innerWidth);
    setPerRow(Math.floor(width / pathWidth));
    setSvgHeight((Math.ceil(flowers.length / perRow) + 0.5) * pathWidth);

    const svg = d3.select(elRef.current);
    svg
      .selectAll("path")
      .data(flowers)
      .enter()
      .append("path")
      .attr(
        "transform",
        (d, i) => `translate(${d.translate})scale(${d.scale || 1})`
      )
      .attr("d", (d) => d.path)
      .attr("fill", (d) => d.color)
      .attr("fill-opacity", 0.75)
      .attr("stroke", (d) => d.color);
  }, [flowers]);

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

export default ScalesExercise;
