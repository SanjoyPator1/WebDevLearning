import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../styles";

const M1SVG = () => {
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 01 - SVG
      </Typography>

      <h4>Exercise 01 - Flower petal</h4>
      <div
        style={{
          width: "120px",
          height: "120px",
          backgroundColor: "white",
          margin: "0 auto",
        }}
      >
        <svg
          width={100}
          height={100}
          style={{ overflow: "visible", margin: "5px" }}
        >
          <path
            d="M0,0 C50,40 50,70 20,100 L0,85 L-20,100 C-50,70 -50,40 0,0"
            fill="lightGreen"
            stroke="#000"
            stroke-width={2}
            transform="translate(50,0)"
          />
        </svg>
      </div>
      <h4>Exercise 02 - Smiley face</h4>
      <div
        style={{
          border: "1px solid black",
          borderRadius: "50%",
          width: "120px",
          height: "120px",
          backgroundColor: "yellow",
          margin: "0 auto",
        }}
      >
        <svg
          width={100}
          height={100}
          style={{ overflow: "visible", margin: "5px" }}
        >
          <path
            d="M25,25 L25,35 M75,25 L75,35 M15,75 C20,100 80,100 85,75"
            fill="none"
            stroke="#000"
            stroke-width={2}
          />
        </svg>
      </div>
      <h4>Exercise 03 - Flower petal</h4>
      <div
        style={{
          width: "120px",
          height: "120px",
          margin: "0 auto",
        }}
      >
        <svg
          width={100}
          height={100}
          style={{ overflow: "visible", margin: "5px" }}
        >
          <path
            d="M0,85     L-20,100 
        C-55,70 -40,50 -30,40     L-20,60
        C-35,20 -10,25 0,0
    
        M0,85     L20,100 
        C55,70 40,50 30,40        L20,60
        C35,20 10,25 0,0"
            fill="#C3EEFF"
            stroke="#000"
            stroke-width={2}
            transform="translate(50,0)"
          />
        </svg>
      </div>

      <hr />
    </div>
  );
};

export default M1SVG;
