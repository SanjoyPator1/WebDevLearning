import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../components/styles";
import React from "react";
import E2TreesClustersAndRadialLayouts from "./02TreesClustersAndRadialLayouts"

const S6HierarchalLayouts = () => {
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 06 - Hierarchal Layouts
      </Typography>

      <h3>Exercise 01 - Paths</h3>
      <div
        style={{
          width: "100%",
          height: "fit-content",
          backgroundColor: "white",
          margin: "0 auto",
        }}
      >
        <E2TreesClustersAndRadialLayouts/>
      </div>
      <hr/>
      
    </div>
  );
};

export default S6HierarchalLayouts;
