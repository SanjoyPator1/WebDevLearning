import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../styles";
import EnterUpdateNewWayJoin from "./EnterUpdateNewWayJoin";
import EnterUpdateOldWay from "./EnterUpdateOldWay";

const M5 = () => {
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 05 - DOM Manipulation
      </Typography>
      <h4>Exercise 01 - Enter-Update Old way</h4>
      <div
        style={{
          border: "1px solid black",
          overflow: "auto",
          backgroundColor: "white",
          padding: 30,
          margin: "0 auto",
        }}
      >
        <EnterUpdateOldWay />
      </div>
      <h4>Exercise 02 - Enter-Update New way Join</h4>
      <div
        style={{
          border: "1px solid black",
          // height: "400px",
          overflow: "auto",
          backgroundColor: "white",
          padding: 30,
          margin: "0 auto",
        }}
      >
        <EnterUpdateNewWayJoin />
      </div>
      <hr />
    </div>
  );
};

export default M5;
