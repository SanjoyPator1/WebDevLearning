import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../components/styles";

const DrawPaths = (svgRefPath) => {
  const svg = d3.select(svgRefPath.current);

  // Create a path generator
  const path = d3.path();

  // Define the starting and ending points for the line
  const startX = 50;
  const startY = 50;
  const endX = 200;
  const endY = 150;

  // Move the path to the starting point
  path.moveTo(startX, startY);

  // Draw a line to the ending point
  path.lineTo(endX, endY);

  //another coordinates for triangle
  path.moveTo(180, 50);
  path.lineTo(250, 50);
  path.lineTo(250, 100);
  path.closePath();

  // Draw the line
  svg.append('path')
    .attr('d', path)
    .attr('stroke', 'blue')
    .attr('stroke-width', 2)
    .attr('fill', 'none');
}

const drawCurves = (svgRefCurves) => {
  const svg = d3.select(svgRefCurves.current);

  // Create a path generator
  const path = d3.path();

  // Define the coordinates for the quadratic curve
  const cpx = 100;
  const cpy = 20;
  const x = 100; //end of quadratic curve
  const y = 100; //end of quadratic curve

  // Move the path to the starting point
  path.moveTo(20, 50); // start of quadratic curve

  // Draw a quadratic curve
  path.quadraticCurveTo(cpx, cpy, x, y);

  // Define the coordinates for the bezier curve
  const cpx1 = 200;
  const cpy1 = 20;
  const cpx2 = 250;
  const cpy2 = 150;
  const bx = 300;
  const by = 100;

  // Move the path to the starting point of the bezier curve
  path.moveTo(150, 50);

  // Draw a bezier curve
  path.bezierCurveTo(cpx1, cpy1, cpx2, cpy2, bx, by);

  // Draw the curves
  svg
    .append("path")
    .attr("d", path)
    .attr("stroke", "red")
    .attr("stroke-width", 2)
    .attr("fill", "none");
};


const E1Paths = () => {

  const svgRefPath = useRef(null);
  const svgRefCurves = useRef(null);

  useEffect(() => {
    DrawPaths(svgRefPath)
    drawCurves(svgRefCurves);
  }, []);

  return (
    <div>
      <h5>Example 01 - Path.moveTo, Path.LineTo, and Path.close </h5>
      <svg
        ref={svgRefPath}
        width={"100%"}
        height={200}
        style={{ border: "1px dashed" }}
      />
      <hr />
      <h5>Example 02 - Curves - (quadratic curve, bezier curve) </h5>
      <svg
        ref={svgRefCurves}
        width={"100%"}
        height={200}
        style={{ border: "1px dashed" }}
      />
    </div>
  );
};

export default E1Paths;

