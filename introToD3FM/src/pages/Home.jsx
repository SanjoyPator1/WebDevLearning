import { Typography } from "@mui/material";
import React, { useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import About from "./About";
import AllProjects from "./AllProjects";
import FilterFlowers from "./FilterFlowers";
import "./Home.css";
import MainProject from "./MainProject";
import { NavBarHead } from "./Style";

function Home() {
  const [open, setOpen] = useState(false);

  const handleToggle = () => {
    setOpen(!open);
  };

  return (
    <div className="App">
      <div className="navBarContainer">
        <nav>
          <div className="logo">
            <Typography variant={"h5"} sx={NavBarHead}>
              Learning D3 with Projects
            </Typography>
          </div>
          <ul className={`nav-links ${open ? "open" : ""}`}>
            <li>
              <Link to="/">HOME</Link>
            </li>
            <li>
              <Link to="/filterFlowers">FILTER FLOWER</Link>
            </li>
            <li>
              <Link to="/allProjects">ALL PROJECTS</Link>
            </li>
            <li>
              <Link to="/about">ABOUT</Link>
            </li>
          </ul>
          <div className="burger" onClick={handleToggle}>
            <div className="line1"></div>
            <div className="line2"></div>
            <div className="line3"></div>
          </div>
        </nav>
        <Routes>
          <Route path="/" element={<MainProject />} />
          <Route path="/filterFlowers" element={<FilterFlowers />} />
          <Route path="/allProjects" element={<AllProjects />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </div>
    </div>
  );
}

export default Home;
