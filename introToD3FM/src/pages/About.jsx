import { Grid, Typography } from "@mui/material";
import {
  BigHeadingStyle,
  BodyTextContainer,
  BodyTextStyle,
  MediumHeadingStyle,
} from "./Style";
import { aboutTextContent } from "./TextContent";
import "./styles.css";

const About = () => {
  return (
    <div
      style={{
        padding: "1.5em",
        width: "70%",
        // backgroundColor: "plum",
        margin: "0 auto",
      }}
    >
      <Typography variant="h6" sx={{ color: "#937DC2", fontFamily: "cursive" }}>
        This website is mainly for learning purpose. No adds are present here
      </Typography>
      <Grid container alignItems={"flex-start"}>
        <Grid item xs={12}>
          <Typography sx={BigHeadingStyle}>ABOUT</Typography>
        </Grid>
        <Grid item sx={{ backgroundColor: "" }} xs={12} md={3}>
          <div style={{ backgroundColor: "" }}>
            <Typography alignItems={"start"} sx={MediumHeadingStyle}>
              this Website
            </Typography>
          </div>
        </Grid>
        <Grid item sx={BodyTextContainer} xs={12} md={7}>
          <Typography sx={BodyTextStyle}>
            {aboutTextContent.firstPara}
          </Typography>
          <Typography sx={BodyTextStyle}>
            {aboutTextContent.secondPara}
          </Typography>
          <Typography sx={BodyTextStyle}>
            {aboutTextContent.thirdPara}
          </Typography>
          <Typography sx={BodyTextStyle}>
            Few topics that I learned while doing all this projects are
          </Typography>
          <ul style={{ display: "block", margin: 0, padding: 0 }}>
            <li>
              <h3>Basics of SVG</h3>
              <ul
                style={{
                  listStyle: "disc",
                  margin: 0,
                  padding: 0,
                  marginLeft: "25px",
                }}
              >
                <li>How SVG Coordinate system works</li>
                <li>How SVG path can be created</li>
              </ul>
            </li>
            <li>
              <h3>API's in D3</h3>
              <ul
                style={{
                  listStyle: "disc",
                  margin: 0,
                  padding: 0,
                  marginLeft: "25px",
                }}
              >
                <li>d3.select() and .selectAll()</li>
                <li>selection.datum() and selection.data()</li>
                <li>selection.attr() and selection.style()</li>
                <li>data Binding</li>
                <li>Create DOM Element from data</li>
                <li>Translate and position</li>
              </ul>
            </li>
            <li>
              <h3>Specifications</h3>
              <ul
                style={{
                  listStyle: "disc",
                  margin: 0,
                  padding: 0,
                  marginLeft: "25px",
                }}
              >
                <li>data Types and Visual Channels</li>
                <li>common scale types with example</li>
                <li>using D3 scales</li>
              </ul>
            </li>
            <li>
              <h3>Groups in D3</h3>
              <ul
                style={{
                  listStyle: "disc",
                  margin: 0,
                  padding: 0,
                  marginLeft: "25px",
                }}
              >
                <li>What are group elements</li>
                <li>grouping elements and nested grouping</li>
              </ul>
            </li>
            <li>
              <h3>Transitions in D3</h3>
              <ul
                style={{
                  listStyle: "disc",
                  margin: 0,
                  padding: 0,
                  marginLeft: "25px",
                }}
              >
                <li>How transition works in D3</li>
                <li>D3's update and exit patterns</li>
                <li>Implementing enter-update old way</li>
                <li>Implementing new way join()</li>
              </ul>
            </li>
            <li>
              <h3>Positioning functions in D3</h3>
              <ul
                style={{
                  listStyle: "disc",
                  margin: 0,
                  padding: 0,
                  marginLeft: "25px",
                }}
              >
                <li>Shapes in D3</li>
                <li>Hierarchy in D3</li>
                <li>Force Layout in D3</li>
              </ul>
            </li>
          </ul>
        </Grid>
      </Grid>
      <Grid
        container
        item
        xs={12}
        style={{ display: "flex", marginBlock: "0.5em" }}
      >
        <Typography
          variant="h6"
          sx={{ color: "#937DC2", fontFamily: "cursive", marginRight: ".5em" }}
        >
          Created by Sanjoy Pator
        </Typography>
        <button class="primary-button">
          <a
            href="https://www.linkedin.com/in/sanjoy-pator-91a41a182/"
            target="_blank"
            class="button"
          >
            LinkedIn
          </a>
        </button>
        <button class="btn-shine" style={{ marginInline: "0.5em" }}>
          <a
            href="https://github.com/SanjoyPator1/WebDevLearning/tree/d3projects/introToD3FM"
            target="_blank"
            class="button"
          >
            <span>Project Repo - GitHub</span>
          </a>
        </button>
      </Grid>
    </div>
  );
};

export default About;
