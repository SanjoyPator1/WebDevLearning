import { Typography } from "@mui/material";
import M1SVG from "../components/FM-Container/01-SVG";
import M2 from "../components/FM-Container/02-API";
import M3 from "../components/FM-Container/03-Specifications";
import M4 from "../components/FM-Container/04-GroupElements";
import M5 from "../components/FM-Container/05-DOMManipulation";
import M6 from "../components/FM-Container/06-Transitions";
import M7 from "../components/FM-Container/07-PositioningFunction";
import M8 from "../components/FM-Container/08-D3-HTML";

export default function AllProjects() {
  return (
    <div className="AllProject" style={{ padding: "1.5em" }}>
      <Typography
        variant="h6"
        sx={{ color: "#937DC2", fontWeight: 500, fontFamily: "cursive" }}
      >
        This project section contains 7 module with different learning items
      </Typography>
      <hr />
      <M1SVG />
      <br />
      <M2 />
      <br />
      <M3 />
      <br />
      <M4 />
      <br />
      <M5 />
      <br />
      <M6 />
      <br />
      <M7 />
    </div>
  );
}
