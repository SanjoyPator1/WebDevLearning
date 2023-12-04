import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../components/styles";

const zoomableCircle = (svgRefZoomableCircles) => {
  // Select the SVG container and remove any existing content
  const svg = d3.select(svgRefZoomableCircles.current);
  svg.selectAll("*").remove();

  // Append a new SVG element to the body
  svg
    .append("svg")
    .attr("width", 460)
    .attr("height", 460);

  // Create a group (g) to contain the circle and other elements
  const group = svg.append("g");

  // Append the circle to the group
  group
    .append("circle")
    .attr("cx", 300)
    .attr("cy", 300)
    .attr("r", 40)
    .style("fill", "#68b2a1")
    .on("mouseover", function () {
      console.log("Mouseover Circle!");
    });

  // Apply zoom behavior to the SVG
  svg.call(
    d3.zoom().on("zoom", function (event) {
      // Log the zoom transformation details
      console.log("Zooming:", event.transform);
      // Apply the zoom transform to the group
      group.attr("transform", event.transform);
    })
  );
};

const zoomableAxes = (svgRefZoomableAxes) => {
    // Select the SVG container and remove any existing content
    const svg = d3.select(svgRefZoomableAxes.current);
    svg.selectAll("*").remove();
  
    // Append a new SVG element to the body
    const width = 460;
    const height = 460;
    svg
      .append("svg")
      .attr("width", width)
      .attr("height", height);
  
    // Set up margins and dimensions
    const margin = { top: 20, right: 20, bottom: 50, left: 50 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
  
    // Dummy data
    const data = [
      { Sepal_Length: 5.1, Petal_Length: 1.4 },
      { Sepal_Length: 4.9, Petal_Length: 1.4 },
      { Sepal_Length: 4.7, Petal_Length: 1.3 },
      // Add more data points as needed
    ];
  
    // Create scales for x and y axes
    const xScale = d3.scaleLinear().domain([4, 8]).range([0, innerWidth]);
    const yScale = d3.scaleLinear().domain([0, 9]).range([innerHeight, 0]);
  
    // Create x and y axes
    const xAxis = d3.axisBottom(xScale);
    const yAxis = d3.axisLeft(yScale);
  
    // Create a group (g) to contain the axes and scatter plot
    const group = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  
    // Append x axis to the group
    group.append("g").attr("class", "x-axis").attr("transform", `translate(0, ${innerHeight})`).call(xAxis);
  
    // Append y axis to the group
    group.append("g").attr("class", "y-axis").call(yAxis);
  
    // Add a clipPath: everything out of this area won't be drawn.
    group.append("defs").append("clipPath")
      .attr("id", "clip")
      .append("rect")
      .attr("width", innerWidth)
      .attr("height", innerHeight);
  
    // Create the scatter variable: where both the circles and the brush take place
    const scatter = group.append('g').attr("clip-path", "url(#clip)");
  
    // Add circles
    scatter
      .selectAll("circle")
      .data(data)
      .enter()
      .append("circle")
        .attr("cx", function (d) { return xScale(d.Sepal_Length); } )
        .attr("cy", function (d) { return yScale(d.Petal_Length); } )
        .attr("r", 8)
        .style("fill", "#61a3a9")
        .style("opacity", 0.5);
  
    // Apply zoom behavior to the SVG
    svg.call(
      d3.zoom().on("zoom", function (event) {
        // Log the zoom transformation details
        console.log("Zooming Axes:", event.transform);
        // Apply the zoom transform to the group containing axes and scatter plot
        group.attr("transform", event.transform);
      })
    );
  };

const zoomAndPanAxes = (svgRefZoomAndPan) => {
    // Create SVG
    const svg = d3.select(svgRefZoomAndPan.current)

    svg.selectAll("*").remove();

    // Chart dimensions
    const width = 500;
    const height = 500;

    // Create scales
    const x = d3.scaleLinear().domain([-1, width + 1]).range([-1, width + 1]);
    const y = d3.scaleLinear().domain([-1, height + 1]).range([-1, height + 1]);

    // Create axes
    const xAxis = d3.axisBottom(x).ticks((width + 2) / (height + 2) * 10).tickSize(height).tickPadding(8 - height);
    const yAxis = d3.axisRight(y).ticks(10).tickSize(width).tickPadding(8 - width);

    // Create zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([1, 40])
      .translateExtent([[-100, -100], [width + 90, height + 100]])
      .filter(filter)
      .on('zoom', zoomed);


      svg.attr('viewBox', [0, 0, width, height]);

    // Append gradient definition
    svg.append('defs').html(`
      <style>
        .axis .domain { display: none; }
        .axis line { stroke-opacity: 0.3; shape-rendering: crispEdges; }
        .view { fill: url(#gradient); stroke: #000; }
      </style>
  
      <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0.0%" stop-color="#2c7bb6"></stop>
        <stop offset="12.5%" stop-color="#00a6ca"></stop>
        <stop offset="25.0%" stop-color="#00ccbc"></stop>
        <stop offset="37.5%" stop-color="#90eb9d"></stop>
        <stop offset="50.0%" stop-color="#ffff8c"></stop>
        <stop offset="62.5%" stop-color="#f9d057"></stop>
        <stop offset="75.0%" stop-color="#f29e2e"></stop>
        <stop offset="87.5%" stop-color="#e76818"></stop>
        <stop offset="100.0%" stop-color="#d7191c"></stop>
      </linearGradient>
    `);

    // Append view rectangle
    const view = svg.append('rect')
      .attr('class', 'view')
      .attr('x', 0.5)
      .attr('y', 0.5)
      .attr('width', width - 1)
      .attr('height', height - 1);

    // Append axes
    const gX = svg.append('g').attr('class', 'axis axis--x').call(xAxis);
    const gY = svg.append('g').attr('class', 'axis axis--y').call(yAxis);

    // Apply zoom behavior
    svg.call(zoom);

    function zoomed({ transform }) {
      view.attr('transform', transform);
      gX.call(xAxis.scale(transform.rescaleX(x)));
      gY.call(yAxis.scale(transform.rescaleY(y)));
    }

    function filter(event) {
      event.preventDefault();
      return (!event.ctrlKey || event.type === 'wheel') && !event.button;
    }
}


const E1SimpleZoom = () => {
  const svgRefZoom = useRef(null);
  const svgRefAxes = useRef(null);
  const svgRefZoomAndPan = useRef(null);
  

  useEffect(() => {
    zoomableCircle(svgRefZoom);
    zoomableAxes(svgRefAxes);
    zoomAndPanAxes(svgRefZoomAndPan)
  }, []);

  return (
    <div>
      <h5>Example 01 - Basic zoom with d3.zoom()</h5>
      <svg
        ref={svgRefZoom}
        width={"100%"}
        height={500}
        style={{ border: "1px dashed" }}
      />
      <h5>Example 02 - Zoomable Axes</h5>
      <svg
        ref={svgRefAxes}
        width={"100%"}
        height={500}
        style={{ border: "1px dashed" }}
      />
      <h5>Example 03 - Zoom and pan Axes</h5>
      <svg
        ref={svgRefZoomAndPan}
        width={"100%"}
        height={500}
        style={{ border: "1px dashed" }}
      />
    </div>
  );
};

export default E1SimpleZoom;
