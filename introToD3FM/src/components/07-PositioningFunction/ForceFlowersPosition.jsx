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
  // const [filteredMovies, setFilteredMovies] = useState([]);
  const [graph, setGraph] = useState(null);

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

  ////////////////////////////////       CREATE SVG D3 CODE HERE            //////////////////////////////////////

  //force position
  const calculateGraph = (prevGraph) => {
    // create an empty object to store genres
    const genres = {};
    // create empty arrays to store nodes and links
    const nodes = [];
    const links = [];
    // console.log("force flowers ", flowers);
    // console.log("force prevGraph ", prevGraph);

    // loop through each item in filtered array
    _.each(movies, (d, i) => {
      // check if the flower is already in the previous graph
      // console.log("force i = ", i);
      let flower;
      flower =
        prevGraph && _.find(prevGraph.nodes, ({ title }) => title === d.title);
      // if not, use the filtered flower
      flower = flower || flowers[i];
      if ((i = 0)) {
        console.log("force first flower from flowers ", flowers[i]);
      }

      // insert flower into nodes
      nodes.push(flower);

      // loop through genres and link the movie flower to the genre
      _.each(d.genres, (genre) => {
        // check if the genre already exists in previous graph's genres object
        if (prevGraph) {
          genres[genre] = _.find(
            prevGraph.genres,
            ({ label }) => label === genre
          );
        }
        // if the genre doesn't exist, create it
        if (!genres[genre]) {
          genres[genre] = {
            label: genre,
            size: 0,
          };
        }
        // increase the genre size by 1
        genres[genre].size += 1;

        // then create a new link between the genre and the movie flower
        links.push({
          source: genres[genre],
          target: flower,
          id: `${genre}-movie${i}`,
        });
      });
    });

    // return an object with nodes, genres, and links
    return { nodes, genres: _.values(genres), links };
  };

  //make force in D3
  useEffect(() => {
    // console.log("force setGraph useEffect");
    if (flowers.length > 0) {
      setGraph((prevGraph) => {
        return calculateGraph(prevGraph);
      });
    }
  }, [flowers]);

  useEffect(() => {
    // let graph = calculateGraph(graph);
    if (flowers.length > 0) {
      console.log("graph force ", graph);

      const link = d3
        .select(elRef.current)
        .selectAll(".link")
        .data(graph.links, (d) => d.id)
        .join("line")
        .classed("link", true)
        .attr("stroke", "#ccc")
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
              _.times(d.numPetals, (i) =>
                Object.assign({}, d, { rotate: i * (360 / d.numPetals) })
              )
            )
            .join("path") //enter+update+exit
            .attr(
              "transform",
              (d) => `rotate(${d.rotate})scale(${0.8 * d.scale})`
            )
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
        .text((d) => d.label)
        .attr("dy", ".35em")
        .attr("text-anchor", "middle");

      //use force simulation
      const nodes = _.union(graph.nodes, graph.genres);
      const simulation = d3
        .forceSimulation(nodes)
        .force("charge", d3.forceManyBody(-300))
        .force("link", d3.forceLink(graph.links).distance(100))
        .force(
          "collide",
          d3.forceCollide((d) => 150 * d.scale || 50)
        )
        .force("center", d3.forceCenter(width / 2, width / 4))
        // .alpha(0.5)
        // .alphaMin(0.1)
        .on("tick", () => {
          flower.attr("transform", (d) => `translate(${d.x},${d.y})`);
          genres.attr("transform", (d) => `translate(${d.x},${d.y})`);
          link
            .attr("x1", (d) => d.source.x)
            .attr("y1", (d) => d.source.y)
            .attr("x2", (d) => d.target.x)
            .attr("y2", (d) => d.target.y);
        });
    }
  }, [graph]);

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

export default ForceFlowersPosition;
