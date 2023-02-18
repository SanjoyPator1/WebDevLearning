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
import { getTrueKeys } from "../../utils/functions";

// const movies = movieData.splice(0, 500);

const ForceFlowersPosition = () => {
  //checkbox - genre
  const [checkboxes, setCheckboxes] = useState({
    action: true,
    comedy: true,
    animation: true,
    drama: true,
    other: true,
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
    G: true,
    PG: true,
    PG13: true,
    R: true,
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

  const pathWidth = 120 + 13;
  const [width, setWidth] = useState(window.innerWidth);
  const [perRow, setPerRow] = useState(Math.floor(width / pathWidth));
  const [svgHeight, setSvgHeight] = useState(
    (Math.ceil(movies.length / perRow) + 0.5) * pathWidth
  );

  const [flowers, setFlowers] = useState([]);
  const [filteredMovies, setFilteredMovies] = useState([]);
  const [graph, setGraph] = useState(null);

  const calculateGridPos = (i) => {
    const x = ((i % perRow) + 0.5) * pathWidth;
    const y = (Math.floor(i / perRow) + 0.5) * pathWidth;
    // console.log(`trans pos x= ${x } & y=${y}`);
    return [x, y];
  };

  const elRef = useRef(null);

  //call this function to generate filtered raw movies data whenever checkbox state changes for both genres and rated
  const createFilterData = () => {
    const filteredGenres = getTrueKeys(checkboxes); //e.g. ["Comedy","Drama"]
    const filteredRated = getTrueKeys(checkboxesRating); //e.g. ["G","PG"]

    const filteredData = movies.filter(
      (movie) =>
        filteredGenres.includes(movie.genres[0].toLowerCase()) &&
        filteredRated.includes(movie.rated)
    );

    console.log("filteredData", filteredData);
    setFilteredMovies(filteredData);
  };

  //filter flowers
  useEffect(() => {
    createFilterData();
  }, [checkboxes, checkboxesRating]);

  //initial flower data setup from filteredMovies data
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
    const minMaxRating = d3.extent(filteredMovies, (d) => d.rating);
    const sizeScale = d3.scaleLinear().domain(minMaxRating).range([0.2, 0.75]);

    // `votes` → `numPetals` (number of petals)
    const minMaxVotes = d3.extent(filteredMovies, (d) => d.votes);
    const numPetalScale = d3
      .scaleQuantize()
      .domain(minMaxVotes)
      .range([5, 6, 7, 8, 9, 10]);

    setFlowers(
      filteredMovies.map((d, i) => ({
        color: colorScale(d.genres[0]),
        path: pathScale(d.rated),
        scale: sizeScale(d.rating),
        numPetals: numPetalScale(d.votes),
        title: d.title,
        translate: calculateGridPos(i),
      }))
    );
  }, [filteredMovies]);

  ////////////////////////////////       CREATE SVG D3 CODE HERE            //////////////////////////////////////
  //after flower data is set
  const createFlowers = () => {
    // console.log("flowers data", flowers);
    const t = d3.select(elRef.current).transition().duration(1000);

    //magic with svg
    // console.log("movies sp", movies);
    setWidth(window.innerWidth);
    setPerRow(Math.floor(width / pathWidth));
    setSvgHeight((Math.ceil(flowers.length / perRow) + 0.5) * pathWidth);

    // ✨ CODE HERE
    const g = d3
      .select(elRef.current)
      .selectAll("g")
      .data(flowers, (d) => d.title)
      .join(
        (enter) => {
          const g = enter
            .append("g")
            .attr("opacity", 0)
            .attr("transform", (d) => `translate(${d.translate})`);
          //create paths and texts
          g.selectAll("path")
            .data((d) =>
              _.times(d.numPetals, (i) => {
                return { rotate: i * (360 / d.numPetals), ...d };
              })
            )
            .join("path") //enter+update+exit
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

          return g;
        },
        (update) => update,
        (exit) => {
          exit.transition(t).attr("opacity", 0).remove();
        }
      )
      .transition(t)
      .attr("opacity", 1)
      .attr("transform", (d) => `translate(${d.translate})`);
  };

  //force position
  const calculateGraph = (prevGraph) => {
    const genres = {};
    const nodes = [];
    const links = [];

    _.each(filtered, (d, i) => {
      let flower;
      flower =
        prevGraph && _.find(prevGraph.nodes, ({ title }) => title === d.title);
      flower = flower || filteredFlowers[i];

      // insert flower into nodes
      nodes.push(flower);

      // loop through genres and link the movie flower to the genre
      _.each(d.genres, (genre) => {
        if (prevGraph) {
          genres[genre] = _.find(
            prevGraph.genres,
            ({ label }) => label === genre
          );
        }
        if (!genres[genre]) {
          // if genre doesn't yet exist, create it
          genres[genre] = {
            label: genre,
            size: 0,
          };
        }
        genres[genre].size += 1;

        // then create a new link
        links.push({
          source: genres[genre],
          target: flower,
          id: `${genre}-movie${i}`,
        });
      });
    });

    return { nodes, genres: _.values(genres), links };
  };

  //make force in D3
  useEffect(() => {
    // let graph = calculateGraph(graph);
    setGraph((prevGraph) => calculateGraph(prevGraph));

    const link = d3
      .select(elRef.current)
      .selectAll("line")
      .data(graph.links, (d) => d.id)
      .join("line")
      .classed("link", true)
      .attr("opacity", 0.5);

    //create flowers
    const flower = d3
      .select(elRef.current)
      .selectAll("g")
      .data(graph.nodes, (d) => d.title)
      .join((enter) => {
        const g = enter.append("g");
        //create paths and texts
        g.selectAll("path")
          .data((d) =>
            _.times(d.numPetals, (i) => {
              return { rotate: i * (360 / d.numPetals), ...d };
            })
          )
          .join("path") //enter+update+exit
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

        return g;
      });

    const genres = d3
      .select(elRef.current)
      .selectAll(".genre")
      .data(graph.genres, (d) => d.label)
      .join("text")
      .classed("genre", true)
      .text((d) => d.title);
    attr("text-anchor", "middle");

    //use force simulation
    const nodes = _.union(graph.nodes, graph.genres);
    const simulation = d3
      .forceSimulation(nodes)
      .force("link", d3.forceLink(graph.links))
      .force(
        "collide",
        d3.forceCollide((d) => d.scale * pathWidth)
      )
      .force("center", d3.forceCenter(width / 2, width / 4))
      .on("tick", () => {
        flower.attr("transform", (d) => `translate(${d.x},${d.y})`);
        genres.attr("transform", (d) => `translate(${d.x},${d.y})`);
        links
          .attr("x1", (d) => d.source.x)
          .attr("y1", (d) => d.source.y)
          .attr("x1", (d) => d.target.x)
          .attr("y1", (d) => d.target.y);
      });
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
        width={width}
        height={svgHeight}
        style={{ border: "1px dashed" }}
      ></svg>
    </div>
  );
};

export default ForceFlowersPosition;
