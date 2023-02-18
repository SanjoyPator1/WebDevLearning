// FilteringAndUpdatingFlowers

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

const FilteringAndUpdatingFlowers = () => {
  //checkbox - genre
  const [checkboxes, setCheckboxes] = useState({
    action: false,
    comedy: false,
    animation: false,
    drama: false,
    other: false,
  });

  const handleCheckboxChange = (event) => {
    const { name, checked } = event.target;
    setCheckboxes({ ...checkboxes, [name]: checked });
  };

  const handleCheckAllChangeGenre = () => {
    setCheckboxes({
      action: true,
      comedy: true,
      animation: true,
      drama: true,
      other: true,
    });
  };

  const handleUncheckAllChangeGenre = () => {
    setCheckboxes({
      action: false,
      comedy: false,
      animation: false,
      drama: false,
      other: false,
    });
  };

  //checkbox - rating
  const [checkboxesRating, setCheckboxesRating] = useState({
    G: false,
    PG: false,
    PG13: false,
    R: false,
  });

  const handleCheckboxChangeRating = (event) => {
    const { name, checked } = event.target;
    setCheckboxesRating({ ...checkboxesRating, [name]: checked });
  };

  const handleCheckAllChangeRatings = () => {
    setCheckboxesRating({
      G: true,
      PG: true,
      PG13: true,
      R: true,
    });
  };

  const handleUncheckAllChangeRatings = () => {
    setCheckboxesRating({
      G: false,
      PG: false,
      PG13: false,
      R: false,
    });
  };

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

  //filter flowers
  useEffect(() => {
    console.log(
      `genres ${checkboxes.action} ${checkboxes.comedy} ${checkboxes.animation} ${checkboxes.drama} ${checkboxes.other}`
    );
    console.log(
      `ratings ${checkboxesRating.G} ${checkboxesRating.PG} ${checkboxesRating.PG13} ${checkboxesRating.R} `
    );
  }, [checkboxes, checkboxesRating]);

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
      <div style={{ position: "sticky", top: 0, zIndex: 1 }}>
        <div
          style={{
            backgroundColor: "black",
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignContent: "flex-start",
            margin: "0.3em",
            padding: "0.3em",
          }}
        >
          <div style={{ width: "fit-content", fontSize: "1.3em" }}>Genres</div>
          <div
            style={{
              display: "flex",
              backgroundColor: "black",
              padding: "10px",
              marginInline: "5px",
            }}
          >
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="action"
                checked={checkboxes.action}
                onChange={handleCheckboxChange}
              />
              Action
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="comedy"
                checked={checkboxes.comedy}
                onChange={handleCheckboxChange}
              />
              Comedy
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="animation"
                checked={checkboxes.animation}
                onChange={handleCheckboxChange}
              />
              Animation
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="drama"
                checked={checkboxes.drama}
                onChange={handleCheckboxChange}
              />
              Drama
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="other"
                checked={checkboxes.other}
                onChange={handleCheckboxChange}
              />
              Other
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="checkAllGenre"
                checked={
                  checkboxes.action &&
                  checkboxes.comedy &&
                  checkboxes.animation &&
                  checkboxes.drama &&
                  checkboxes.other
                }
                onChange={handleCheckAllChangeGenre}
              />
              Check all
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="uncheckAllGenre"
                checked={
                  !checkboxes.action &&
                  !checkboxes.comedy &&
                  !checkboxes.animation &&
                  !checkboxes.drama &&
                  !checkboxes.other
                }
                onChange={handleUncheckAllChangeGenre}
              />
              Uncheck all
            </label>
          </div>
        </div>
        <div
          style={{
            backgroundColor: "black",
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignContent: "flex-start",
            margin: "0.3em",
            padding: "0.3em",
          }}
        >
          <div style={{ width: "fit-content", fontSize: "1.3em" }}>
            Parental Guidance Ratings
          </div>
          <div
            style={{
              display: "flex",
              backgroundColor: "black",
              padding: "10px",
              marginInline: "5px",
            }}
          >
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="G"
                checked={checkboxesRating.G}
                onChange={handleCheckboxChangeRating}
              />
              G
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="PG"
                checked={checkboxesRating.PG}
                onChange={handleCheckboxChangeRating}
              />
              PG
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="PG13"
                checked={checkboxesRating.PG13}
                onChange={handleCheckboxChangeRating}
              />
              PG-13
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="R"
                checked={checkboxesRating.R}
                onChange={handleCheckboxChangeRating}
              />
              R
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="checkAllGenre"
                checked={
                  checkboxesRating.G &&
                  checkboxesRating.PG &&
                  checkboxesRating.PG13 &&
                  checkboxesRating.R
                }
                onChange={handleCheckAllChangeRatings}
              />
              Check all
            </label>
            <label style={{ marginInline: "5px" }}>
              <input
                type="checkbox"
                name="uncheckAllGenre"
                checked={
                  !checkboxesRating.G &&
                  !checkboxesRating.PG &&
                  !checkboxesRating.PG13 &&
                  !checkboxesRating.R
                }
                onChange={handleUncheckAllChangeRatings}
              />
              Uncheck all
            </label>
          </div>
        </div>
      </div>
      <svg
        ref={elRef}
        width={width - "15%"}
        height={svgHeight}
        style={{ border: "1px dashed" }}
      ></svg>
    </div>
  );
};

export default FilteringAndUpdatingFlowers;
