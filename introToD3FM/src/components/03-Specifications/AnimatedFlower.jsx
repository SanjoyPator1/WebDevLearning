import React, { useRef, useEffect } from "react";
import * as d3 from "d3";

const AnimatedSolarSystem = () => {
  const svgRef = useRef(null);

  useEffect(() => {
    const svg = d3.select(svgRef.current);

    const width = +svg.attr("width");
    const height = +svg.attr("height");

    const planets = [
      { name: "Mercury", radius: 10, distance: 60 },
      { name: "Venus", radius: 15, distance: 90 },
      { name: "Earth", radius: 20, distance: 120 },
      { name: "Mars", radius: 10, distance: 150 },
      { name: "Jupiter", radius: 40, distance: 240 },
      { name: "Saturn", radius: 35, distance: 300 },
      { name: "Uranus", radius: 25, distance: 360 },
      { name: "Neptune", radius: 20, distance: 420 }
    ];

    const solarSystem = svg
      .append("g")
      .attr("transform", `translate(${width / 2}, ${height / 2})`);

    const circles = solarSystem
      .selectAll("circle")
      .data(planets)
      .enter()
      .append("circle")
      .attr("cx", (d) => d.distance)
      .attr("cy", 0)
      .attr("r", (d) => d.radius)
      .style("fill", (d) => {
        switch (d.name) {
          case "Mercury":
            return "brown";
          case "Venus":
            return "yellow";
          case "Earth":
            return "blue";
          case "Mars":
            return "red";
          case "Jupiter":
            return "orange";
          case "Saturn":
            return "khaki";
          case "Uranus":
            return "lightblue";
          case "Neptune":
            return "darkblue";
        }
      });

    solarSystem
      .selectAll("circle")
      .transition()
      .duration(5000)
      .attrTween("transform", function (d) {
        const i = d3.interpolate(0, Math.PI * 2);
        return function (t) {
          return `translate(${
            d.distance * Math.cos(i(t))
          }, ${d.distance * Math.sin(i(t))})`;
        };
      })
      .on("end", function repeat() {
        d3.active(this)
          .transition()
          .duration(5000)
          .attrTween("transform", function (d) {
            const i = d3.interpolate(0, Math.PI * 2);
            return function (t) {
              return `translate(${
                d.distance * Math.cos(i(t))
              }, ${d.distance * Math.sin(i(t))})`;
            };
          })
          .on("end", repeat);
      });
  }, []);
  return (
    <svg width="400" height="400" ref={svgRef}>
      {" "}
    </svg>
  );
};

export default AnimatedSolarSystem;
