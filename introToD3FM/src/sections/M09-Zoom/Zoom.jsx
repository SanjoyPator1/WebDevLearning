import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../components/styles";
import React from "react";
import E1SimpleZoom from "./01SimpleZoom";
import E2ZoomableTimeline from "./02ZoomableTimeline";

const S9Zoom = () => {
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 09 - Zoom
      </Typography>

      <h3>Exercise 01 - Zoom basics</h3>
      <div
        style={{
          width: "100%",
          height: "fit-content",
          backgroundColor: "white",
          margin: "0 auto",
        }}
      >
        <E1SimpleZoom/>
      </div>
      <hr/>
      <h3>Exercise 02 - Zoomable timeline</h3>
      <div
        style={{
          width: "100%",
          height: "fit-content",
          backgroundColor: "white",
          margin: "0 auto",
        }}
      >
        <E2ZoomableTimeline/>
      </div>
      <hr/>
    </div>
  );
};

export default S9Zoom;
