import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import ReactDOMServer from "react-dom/server";
import { formatDataForTimeline } from "../../utils/functions";

const E2ZoomableTimeline = () => {
  // Refs to store references to the SVG and container elements
  const svgRefZoom = useRef(null);
  const containerRef = useRef(null);

  // Variables for axis group, height, and initial data
  let xAxisGroup;
  let height = 200;

  useEffect(() => {
    // Function to calculate container width
    const containerWidth = containerRef.current.offsetWidth;

    // Selecting the SVG element and removing any existing elements inside it
    const svg = d3.select(svgRefZoom.current);
    svg.selectAll("*").remove();

    const startDateRaw = new Date("2021-12-31");
    const endDateRaw = new Date("2024-01-31");

    // // Data for timeline events
    const dataRaw = [
      { date: new Date("2022-02-15"), title: "Event 1", status: "In Progress" },
      { date: new Date("2022-03-20"), title: "Event 2", status: "Pending" },
      { date: new Date("2022-04-05"), title: "Event 3", status: "Completed" },
      { date: new Date("2022-06-10"), title: "Event 4", status: "In Progress" },
      { date: new Date("2022-08-25"), title: "Event 5", status: "Pending" },
      { date: new Date("2023-01-08"), title: "Event 6", status: "Completed" },
      { date: new Date("2023-03-18"), title: "Event 7", status: "In Progress" },
      { date: new Date("2023-05-22"), title: "Event 8", status: "Pending" },
      { date: new Date("2023-12-25"), title: "Event 9", status: "Completed" },
    ];

    const { startDate, endDate, formattedData } = formatDataForTimeline(startDateRaw, endDateRaw, dataRaw);

    // Creating X scale based on time
    const xScale = d3.scaleTime().domain([startDate, endDate]).range([0, containerWidth]);
    const xAxis = d3.axisBottom(xScale);

    // Initial transformation for the timeline view
    const initialMonthTransform = d3.zoomIdentity
      .scale(containerWidth / (xScale(endDate) - xScale(startDate)))
      .translate(0, 0);

    // Zoom behavior definition
    const zoom = d3.zoom()
      .scaleExtent([1, 60])
      .translateExtent([[0, 0], [containerWidth, height]])
      .on("zoom", zoomed);

    // Setting up the SVG with zoom behavior and initial transformation
    svg
      .attr("width", "100%")
      .attr("height", height)
      .call(zoom)
      .call(zoom.transform, initialMonthTransform);

    // Adding a background rectangle to the SVG
    svg.append("rect")
      .attr("width", "100%")
      .attr("height", height)
      .attr("fill", "#e6ffff");

    // Adding X axis to the SVG
    xAxisGroup = svg.append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0, ${height / 2 + 50})`)
      .call(xAxis);

    // Adding circles for each event on the timeline
    svg.selectAll("circle")
      .data(formattedData)
      .enter()
      .append("circle")
      .attr("cx", (d) => {
        const xPosition = xScale(d.date);
        console.log(`Circle at position ${xPosition} for date ${d.date}`);
        return xPosition;
      })
      .attr("cy", height / 2) // Adjusted vertical position
      .attr("r", 5)
      .attr("fill", (d) => {
        // Color coding based on event status and date
        if (d.date > new Date()) {
          return "red";
        } else {
          switch (d.status) {
            case "Pending":
              return "gray";
            case "In Progress":
              return "orange";
            case "Completed":
              return "green";
            default:
              return "steelblue";
          }
        }
      })
      // Adding tooltip on mouseover event
      .on("mouseover", function (event, d) {
        const tooltipPosition = {
          x: event.offsetX,
          y: event.offsetY - 20,
        };

        const tooltipContent = (
          // Creating a React element for tooltip content
          <div
            style={{
              background: "#333",
              color: "#fff",
              padding: "5px",
              borderRadius: "5px",
              fontSize: "12px",
            }}
          >
            {d3.timeFormat("%d %b")(d.date)} - {d.title}
          </div>
        );

        // Rendering React element to string for HTML insertion
        const tooltipString = ReactDOMServer.renderToString(tooltipContent);

        // Appending a foreignObject to display the tooltip
        svg
          .append("foreignObject")
          .attr("class", "tooltip")
          .attr("width", 150)
          .attr("height", 40)
          .attr("x", tooltipPosition.x)
          .attr("y", tooltipPosition.y)
          .html(() => tooltipString);
      })
      // Removing tooltip on mouseout event
      .on("mouseout", function () {
        svg.select(".tooltip").remove();
      });

    // Function to handle zooming
    function zoomed(event) {
      const { transform } = event;
      const newXScale = transform.rescaleX(xScale);

      if (!xAxisGroup) return;

      // Updating X axis and tick labels during zoom
      xAxisGroup.call(xAxis.scale(newXScale));

      // Adjusting tick labels based on zoom level
      if (transform.k > 8) {
        const tickValues = xAxis.scale().ticks();
        xAxisGroup
          .selectAll(".tick text")
          .text((d, i) => {
            const formattedDate = d3.timeFormat("%d %b - %y")(new Date(tickValues[i]));
            console.log(`Tick at position ${newXScale(new Date(tickValues[i]))} with date ${formattedDate}`);
            return formattedDate;
          });
      } else {
        xAxisGroup.selectAll(".tick text").text((d) => {
          const formattedDate = d3.timeFormat("%b - %y")(d);
          console.log(`Tick at position ${newXScale(d)} with date ${formattedDate}`);
          return formattedDate;
        });
      }

      // Updating circle positions based on new X scale during zoom
      svg.selectAll("circle").attr("cx", (d) => {
        const xPosition = newXScale(d.date);
        console.log(`Circle at position ${xPosition} for date ${d.date}`);
        return xPosition;
      });
    }
  }, []); // Empty dependency array to run useEffect only once

  // Returning the component JSX
  return (
    <div style={{ width: "100%" }} ref={containerRef}>
      <svg
        ref={svgRefZoom}
        height={height}
        style={{ border: "1px dashed" }}
      />
    </div>
  );
};

export default E2ZoomableTimeline;
