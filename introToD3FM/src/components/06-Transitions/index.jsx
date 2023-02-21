import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../styles";
import AnimateWithTranisitionBarGraph from "./AnimateWithTranisitionBarGraph";
import FilteringAndUpdatingFlowers from "./FilteringAndUpdatingFlowers";

const M6 = () => {
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 06 - transitions
      </Typography>
      <h4>Exercise 01 - Animate with Transitions - bar graph</h4>
      <div
        style={{
          border: "1px solid black",
          overflow: "auto",
          backgroundColor: "white",
          padding: 30,
          margin: "0 auto",
        }}
      >
        <AnimateWithTranisitionBarGraph />
      </div>
      <h4>Exercise 02 - Filtering and Updating data - Flower data</h4>
      <div
        style={{
          justifyContent: "center",
          border: "1px solid black",
          height: "800px",
          overflow: "auto",
          backgroundColor: "white",
          padding: "30",
          margin: "0 auto",
          marginBlock: "0.5em",
        }}
      >
        <FilteringAndUpdatingFlowers />
      </div>
      <br />
      <hr />
      <br />
    </div>
  );
};

export default M6;
