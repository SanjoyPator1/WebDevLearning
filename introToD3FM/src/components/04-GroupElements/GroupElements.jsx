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
import _ from "lodash";

// const movies = movieData.splice(0, 500);

const GroupElements = () => {
  const pathWidth = 120 + 13;
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

    // console.log("topGenres", topGenres);
    // console.log("petalColors", petalColors);
    // console.log("colorObj", colorObj);
    // console.log("petalPaths", petalPaths);

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
    // console.log("flowers data", flowers);

    //magic with svg
    // console.log("movies sp", movies);
    setWidth(window.innerWidth);
    setPerRow(Math.floor(width / pathWidth));
    setSvgHeight((Math.ceil(flowers.length / perRow) + 0.5) * pathWidth);

    // ✨ OUR CODE HERE
    const g = d3
      .select(elRef.current)
      .selectAll("g")
      .data(flowers)
      .enter()
      .append("g")
      .attr("transform", (d) => `translate(${d.translate})`);

    //create our petal paths
    g.selectAll("path")
      .data((d) => {
        return _.times(d.numPetals, (i) => {
          // create a copy of the parent data, and add in calculated rotation
          return Object.assign({}, d, { rotate: i * (360 / d.numPetals) });
        });
      })
      .enter()
      .append("path")
      .attr("transform", (d) => `rotate(${d.rotate})scale(${d.scale})`)
      .attr("d", (d) => d.path)
      .attr("fill", (d) => d.color)
      .attr("fill-opacity", 0.5)
      .attr("stroke", (d) => d.color)
      .attr("stroke-width", 2);

    //create our text titles
    g.append("text")
      .text((d) => _.truncate(d.title, 10))
      .style("font-size", ".7em")
      .style("font-style", "italic")
      .attr("text-anchor", "middle")
      .attr("dy", ".35em");
  }, [flowers]);

  return (
    <div>
      <svg
        ref={elRef}
        width={width}
        height={svgHeight}
        style={{ border: "1px dashed", padding: "10px" }}
      ></svg>
    </div>
  );
};

export default GroupElements;
