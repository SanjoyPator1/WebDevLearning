import React, { useRef, useEffect } from "react";
import * as d3 from "d3";

const FormWithD3 = () => {
  const svgRef = useRef(null);
  const dateRef = useRef(null);
  const distance = 80;

  useEffect(() => {
    const svg = d3.select(svgRef.current);

    // Add galaxy background
    const galaxy = svg
      .selectAll("circle")
      .data(d3.range(200))
      .enter()
      .append("circle")
      .attr("cx", (d) => Math.random() * 500)
      .attr("cy", (d) => Math.random() * 500)
      .attr("r", (d) => Math.random() * 2)
      .style("fill", "white")
      .style("opacity", (d) => Math.random() * 0.5 + 0.5);

    const sunWidth = 40;
    const sunHeight = 40;

    const sun = svg
      .append("circle")
      .attr("cx", 250)
      .attr("cy", 250)
      .attr("r", 40)
      .style("fill", "url(#sunGradient)");

    const filter = svg
      .append("defs")
      .append("filter")
      .attr("id", "blur")
      .append("feGaussianBlur")
      .attr("stdDeviation", 2);

    sun.style("filter", "url(#blur)");

    const defs = svg.append("defs");

    const sunGradient = defs
      .append("radialGradient")
      .attr("id", "sunGradient")
      .attr("cx", "50%")
      .attr("cy", "50%")
      .attr("r", "50%");

    sunGradient
      .append("stop")
      .attr("offset", "0%")
      .style("stop-color", "rgb(255,255,102)");

    sunGradient
      .append("stop")
      .attr("offset", "100%")
      .style("stop-color", "rgb(255,178,102)");

    sun
      .transition()
      .duration(2000)
      .ease(d3.easeSin)
      .attr("r", 45)
      .transition()
      .duration(5000)
      .ease(d3.easeSin)
      .attr("r", 40);

    //flare
    const flareTransition = function () {
      d3.select(this)
        .transition()
        .duration(3000)
        .ease(d3.easeLinear)
        .delay((d) => Math.random() * 3000)
        .attr("cx", (d) => 250 + (Math.random() - 0.5) * 100)
        .attr("cy", (d) => 250 + (Math.random() - 0.5) * 100)
        .attr("r", 0)
        .style("opacity", 0)
        .on("end", function () {
          d3.select(this)
            .transition()
            .duration(3000)
            .ease(d3.easeLinear)
            .delay((d) => Math.random() * 3000)
            .attr("cx", 250)
            .attr("cy", 250)
            .attr("r", (d) => (Math.random() + 0.5) * 15)
            .style("opacity", 0.5)
            .on("end", function () {
              d3.select(this).call(flareTransition);
            });
        });
    };
    const flares = svg
      .selectAll("flare")
      .data(d3.range(10))
      .enter()
      .append("circle")
      .attr("cx", 250)
      .attr("cy", 250)
      .attr("r", (d) => (Math.random() + 0.5) * 15)
      .style("fill", "orange")
      .style("opacity", 0.5)
      .transition()
      .duration(3000)
      .ease(d3.easeLinear)
      .delay((d) => Math.random() * 3000)
      .attr("cx", (d) => 250 + (Math.random() - 0.5) * 100)
      .attr("cy", (d) => 250 + (Math.random() - 0.5) * 100)
      .attr("r", 0)
      .style("opacity", 0)
      .on("end", function () {
        d3.select(this)
          .transition()
          .duration(3000)
          .ease(d3.easeLinear)
          .delay((d) => Math.random() * 3000)
          .attr("cx", 250)
          .attr("cy", 250)
          .attr("r", (d) => (Math.random() + 0.5) * 15)
          .style("opacity", 0.5)
          .on("end", function () {
            d3.select(this).call(flareTransition);
          });
      });

    flares.each(function () {
      d3.select(this).call(flareTransition);
    });

    const sunRotation = function () {
      d3.select(sun)
        .transition()
        .duration(5000)
        .ease(d3.easeLinear)
        .attrTween("transform", function () {
          return d3.interpolateString(
            "rotate(0," + sunWidth / 2 + "," + sunHeight / 2 + ")",
            "rotate(360," + sunWidth / 2 + "," + sunHeight / 2 + ")"
          );
        })
        .on("end", function () {
          d3.select(this).call(sunRotation);
        });
    };

    d3.select(sun).call(sunRotation);

    const earthOrbit = d3
      .arc()
      .innerRadius(distance)
      .outerRadius(distance)
      .startAngle(0)
      .endAngle(2 * Math.PI);

    const orbitPath = svg
      .append("path")
      .attr("d", earthOrbit)
      .attr("transform", `translate(${250}, ${250})`)
      .style("fill", "none")
      .style("stroke", "grey")
      .style("opacity", 0.3);

    const earth = svg
      .append("circle")
      .attr("cx", 250 + distance)
      .attr("cy", 250)
      .attr("r", 14)
      .call(
        d3.drag().on("drag", function (event) {
          const x = event.x;
          const y = event.y;
          const angle = Math.atan2(y - 250, x - 250);
          const earthX = 250 + distance * Math.cos(angle);
          const earthY = 250 + distance * Math.sin(angle);
          earth.attr("cx", earthX).attr("cy", earthY);
          const date = calculateDate(earthX, earthY);
          dateRef.current.value = date;
        })
      );

    earth.style("filterEarth", "url(#blur)");

    const radialGradient = svg
      .append("defs")
      .append("radialGradient")
      .attr("id", "earthGradient");

    radialGradient
      .append("stop")
      .attr("offset", "10%")
      .attr("stop-color", "lightGreen");

    radialGradient
      .append("stop")
      .attr("offset", "100%")
      .attr("stop-color", "lightblue");

    earth.style("fill", "url(#earthGradient)");

    const planets = [
      {
        orbitRadius: 55,
        planetColor: "#c9a227",
        angle: 0.05,
        radius: 5,
        ring: false,
      },
      {
        orbitRadius: 65,
        planetColor: "#ff9b85",
        angle: 0.03,
        radius: 7,
        ring: false,
      },
      {
        orbitRadius: 120,
        planetColor: "#db3a34",
        angle: 0.01,
        radius: 8,
        ring: false,
      },
      {
        orbitRadius: 150,
        planetColor: "#ff9100",
        angle: 0.03,
        radius: 10,
        ring: false,
      },
      {
        orbitRadius: 180,
        planetColor: "#4281a4",
        angle: 0.02,
        radius: 11,
        ring: true,
      },
      {
        orbitRadius: 210,
        planetColor: "#004e89",
        angle: 0.01,
        radius: 9,
        ring: false,
      },
    ];

    //extra planets
    // Define the orbiting radius
    let sunX = 250;
    let sunY = 250;

    planets.map((item) => {
      let angle = item.angle;
      const orbitRadius = item.orbitRadius;
      // Define the position of the planet based on its angle
      let planetX = orbitRadius * Math.cos(angle) + sunX;
      let planetY = orbitRadius * Math.sin(angle) + sunY;

      // Create the planet
      const planet = svg
        .append("circle")
        .attr("cx", planetX)
        .attr("cy", planetY)
        .attr("r", item.radius)
        .style("fill", item.planetColor);
      const hasRing = item.ring;

      let ring;
      // Add the ring
      if (hasRing) {
        const ringInnerRadius = item.radius + 3;
        const ringOuterRadius = item.radius + 5;
        const ringArc = d3
          .arc()
          .innerRadius(ringInnerRadius)
          .outerRadius(ringOuterRadius)
          .startAngle(0)
          .endAngle(2 * Math.PI);
        ring = svg
          .append("path")
          .attr("d", ringArc)
          .attr("transform", `translate(${planetX},${planetY})`)
          .style("fill", "none")
          .style("stroke", "yellow")
          .style("stroke-width", "1");
      }

      // Define the orbit path of the planet
      const planetOrbit = d3
        .arc()
        .innerRadius(orbitRadius)
        .outerRadius(orbitRadius)
        .startAngle(0)
        .endAngle(2 * Math.PI);

      const planetOrbitPath = svg
        .append("path")
        .attr("d", planetOrbit)
        .attr("transform", `translate(${250}, ${250})`)
        .style("fill", "none")
        .style("stroke", "grey")
        .style("opacity", 0.3);

      // Update the position of the planet in a loop
      d3.interval(function () {
        angle += item.angle;
        planetX = orbitRadius * Math.cos(angle) + sunX;
        planetY = orbitRadius * Math.sin(angle) + sunY;
        planet.attr("cx", planetX).attr("cy", planetY);
        if (hasRing) {
          ring.attr("transform", `translate(${planetX},${planetY})`);
        }
      }, 100);
    });
  }, []);

  function calculateDate(x, y) {
    // Calculate the date based on the earth's position
    let angle = Math.atan2(y - 250, x - 250);
    angle = angle < 0 ? 2 * Math.PI + angle : angle;
    let date = new Date(2023, 0, 1);
    let year = date.getFullYear();
    date.setDate(date.getDate() + (angle / (2 * Math.PI)) * 365);
    if (date.getFullYear() > year) {
      date.setFullYear(year + 1);
    }
    return date.toISOString().slice(0, 10);
  }

  return (
    <div style={{ position: "relative", backgroundColor: "black" }}>
      <div
        style={{
          position: "absolute",
          top: -10,
          left: 330,
        }}
      >
        <form style={{ transform: "translateY(10px)" }}>
          <label
            style={{ marginRight: "20px", fontSize: "12px" }}
            htmlFor="name"
          >
            Name:
          </label>
          <input type="text" id="name" name="name" />
          <br />
          <br />
          <label
            style={{ marginRight: "20px", fontSize: "12px" }}
            htmlFor="dob"
          >
            Date of Birth:
          </label>
          <input type="text" id="dob" name="dob" ref={dateRef} readOnly />
        </form>
      </div>
      <svg width={600} height={500} ref={svgRef} />
      <div
        style={{
          position: "absolute",
          top: -10,
          left: 30,
        }}
      >
        <p style={{ fontsize: "1px" }}>When Client says : </p>
        <p>"Be Creative with the Date Picker"</p>
      </div>
    </div>
  );
};

export default FormWithD3;
