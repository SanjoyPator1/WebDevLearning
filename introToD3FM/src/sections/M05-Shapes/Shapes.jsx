import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../components/styles";
import React from "react";
import E1Paths from "./01Paths";
import E8Links from "./08Links";

const S1Shapes = () => {
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 05 - Shapes
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
        <E1Paths/>
      </div>
      <hr/>
      <h3>Exercise 08 - Links</h3>
      <div
        style={{
          width: "100%",
          height: "fit-content",
          backgroundColor: "white",
          margin: "0 auto",
        }}
      >
        <E8Links/>
      </div>
      <hr/>
      

      <hr />
    </div>
  );
};

export default S1Shapes;
