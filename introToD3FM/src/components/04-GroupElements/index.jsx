import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../styles";
import GroupElements from "./GroupElements";

const M4 = () => {
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 04 - Group Elements
      </Typography>
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
        <GroupElements />
      </div>
      <hr />
    </div>
  );
};

export default M4;
