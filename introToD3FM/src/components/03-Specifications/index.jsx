import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../styles";
import AnimatedFlower from "./AnimatedFlower";
import ScalesExercise from "./ScalesExercise";
import ScalesImplementation from "./ScalesImplementation";
import TranslateAndScale from "./TranslateAndScale";

const M3 = () => {
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 03 - Specifications
      </Typography>
      <h4>Exercise 01 - Selections</h4>
      <div
        style={{
          border: "1px solid black",
          height: "fit-content",
          backgroundColor: "white",
          padding: 10,
          margin: "0 auto",
        }}
      >
        <ScalesImplementation />
      </div>
      <h4>Exercise 02 - Scales Exercise</h4>
      <div
        style={{
          justifyContent: "center",
          border: "1px solid black",
          width: "100%",
          height: "500px",
          overflow: "auto",
          backgroundColor: "white",
          padding: "20",
          margin: "0 auto",
        }}
      >
        <ScalesExercise />
      </div>
      <h4>Exercise 03 - Translate And Scale</h4>
      <div
        style={{
          border: "1px solid black",
          overflow: "auto",
          backgroundColor: "white",
          padding: 30,
          margin: "0 auto",
        }}
      >
        <TranslateAndScale />
      </div>
      <hr />
    </div>
  );
};

export default M3;
