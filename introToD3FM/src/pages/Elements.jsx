import React from "react";
import { Typography } from "@mui/material";
import S1Shapes from "../sections/M05-Shapes/Shapes";
import S6HierarchalLayouts from "../sections/M06-HierarchalLayouts/HierarchalLayouts";
import S9Zoom from "../sections/M09-Zoom/Zoom";


const Elements = () => {
  return (
    <div className="AllProject" style={{ padding: "1.5em" }}>
      <Typography
        variant="h6"
        sx={{ color: "#937DC2", fontWeight: 500, fontFamily: "cursive" }}
      >
        This project section contains different elements of D3.js
      </Typography>
      <hr />
      <S1Shapes/>
      <br />
      <S6HierarchalLayouts/>
      <br/>
      <S9Zoom/>
    </div>
  );
}

export default Elements;
