import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../components/styles";

const linkVertical = (svgRefVertical) => {
    const svg = d3.select(svgRefVertical.current);

    // Create a link generator for vertical links
    const linkGenerator = d3.linkVertical()
        .source(d => d.source)
        .target(d => d.target);

    const multiLinkData = [
        { source: [150, 25], target: [50, 100] },
        { source: [150, 25], target: [250, 100] },
    ];

    // Draw the links
    svg.selectAll("path")
        .data(multiLinkData)
        .join("path")
        .attr("d", linkGenerator)
        .attr("fill", "none")
        .attr("stroke", "blue")
        .attr("stroke-width", 1);
};

const linkHorizontal = (svgRefHorizontal) => {
    const svg = d3.select(svgRefHorizontal.current);

    // Create a link generator for horizontal links
    const linkGenerator = d3.linkHorizontal()
        .source(d => d.source)
        .target(d => d.target);

    // Define the link data
    const multiLinkData = [
        { source: [50, 100], target: [150, 30] },
        { source: [50, 100], target: [150, 170] },
    ];

    // Draw the links
    svg.selectAll("path")
        .data(multiLinkData)
        .join("path")
        .attr("d", linkGenerator)
        .attr("fill", "none")
        .attr("stroke", "blue")
        .attr("stroke-width", 1);
};

const linkRadial = (svgRefRadial) => {
    const svg = d3.select(svgRefRadial.current);

    // Create a link generator for radial links
    const linkGenerator = d3.linkRadial()
        .angle(d => d.angle)
        .radius(d => d.radius);

    // Define the link data
    const data = {
        source: { angle: Math.PI / 2, radius: 50 },
        target: { angle: Math.PI, radius: 100 }
    };

    // Draw the link
    svg.append('path')
        .attr('d', linkGenerator(data))
        .attr('stroke', 'red')
        .attr('stroke-width', 1)
        .attr('fill', 'none');
};

const linkSourceAndTarget = (svgRef) => {
    const svg = d3.select(svgRef.current);

    // Create a link generator for horizontal links
    const linkGenerator = d3.linkHorizontal()
        .source(d => d.parentPosition)
        .target(d => d.position);

    // Define the link data
    const nodeData = [
        { id: "D3", position: [100, 25], parentPosition: [100, 25] },
        { id: "Scales", position: [25, 175], parentPosition: [100, 25] },
        { id: "Shapes", position: [175, 175], parentPosition: [100, 25] }
    ];

    // Draw the links
    svg.selectAll("path")
        .data(nodeData) // Exclude the first node as it has no parent
        .join("path")
        .attr("d", linkGenerator)
        .attr("fill", "none")
        .attr("stroke", "blue")
        .attr("stroke-width", 1);
};

const linkPositionScaleVertical = (svgRef) => {
    const svg = d3.select(svgRef.current);

    // Define the node data
    const nodeData = [
        { id: "D3", position: [2, 0], parentPosition: [2, 0] },
        { id: "Shapes", position: [1, 1], parentPosition: [2, 0] },
        { id: "Scales", position: [3, 1], parentPosition: [2, 0] },
        { id: "Links", position: [0, 2], parentPosition: [1, 1] },
        { id: "Areas", position: [1, 2], parentPosition: [1, 1] },
        { id: "Arcs", position: [2, 2], parentPosition: [1, 1] },
        { id: "Ordinal", position: [3, 2], parentPosition: [3, 1] },
        { id: "Quantize", position: [4, 2], parentPosition: [3, 1] }
    ];

    // Define the scales
    const xScale = d3.scaleLinear().domain([0, 4]).range([25, 175]);
    const yScale = d3.scaleLinear().domain([0, 2]).range([25, 175]);

    // Create a link generator for vertical links
    const linkGenerator = d3.linkVertical()
        .source(d => d.position)
        .target(d => d.parentPosition)
        .x(d => xScale(d[0]))
        .y(d => yScale(d[1]));

    // Draw the links
    svg.selectAll("path")
        .data(nodeData.slice(1)) // Exclude the first node as it has no parent
        .join("path")
        .attr("d", linkGenerator)
        .attr("fill", "none")
        .attr("stroke", "blue")
        .attr("stroke-width", 1);
};

//for dynamic positioning - when we don't know the exact position
const linkPositionScaleHorizontal = (svgRef) => {
    const svg = d3.select(svgRef.current);

    // Define the node data
    const nodeData = [
        { id: "D3", position: [0, 2], parentPosition: [0, 2] },
        { id: "Shapes", position: [2, 4], parentPosition: [0, 2] },
        { id: "Scales", position: [2, 1], parentPosition: [0, 2] },
        { id: "Links", position: [3, 5], parentPosition: [2, 4] },
        { id: "Areas", position: [3, 4], parentPosition: [2, 4] },
        { id: "Arcs", position: [3, 3], parentPosition: [2, 4] },
        { id: "Ordinal", position: [3, 1], parentPosition: [2, 1] },
        { id: "Quantize", position: [3, 0], parentPosition: [2, 1] }
    ];


    // Define the scales
    const xScale = d3.scaleLinear()
        .domain([0, 3])
        .range([25, 175]);
    const yScale = d3.scaleLinear().domain([0, 5]).range([25, 200]);

    // Create a link generator for horizontal links
    const linkGenerator = d3.linkHorizontal()
        .source(d => d.position)
        .target(d => d.parentPosition)
        .x(d => xScale(d[0]))
        .y(d => yScale(d[1]));

    // Draw the links
    svg.selectAll("path")
        .data(nodeData.slice(1)) // Exclude the first node as it has no parent
        .join("path")
        .attr("d", linkGenerator)
        .attr("fill", "none")
        .attr("stroke", "green")
        .attr("stroke-width", 1);
};

const convertLinksVerticalHorizontal = (svgRef, type) => {
    const multiLinkData = [
        { source: [150, 25], target: [50, 100] },
        { source: [150, 25], target: [250, 100] },
    ];

    const svg = d3.select(svgRef.current);
    let linkGenerator;

    if (type === "vertical") {
        // Create a link generator for vertical links
        linkGenerator = d3.linkVertical()
            .source(d => d.source)
            .target(d => d.target);
    } else if (type === "horizontal") {
        // Create a link generator for horizontal links
        linkGenerator = d3.linkHorizontal()
            .source(d => [d.source[1], d.source[0]]) // Flip x and y positions
            .target(d => [d.target[1], d.target[0]]); // Flip x and y positions
    }

    // Draw the links
    svg.selectAll("path")
        .data(multiLinkData)
        .join("path")
        .attr("d", linkGenerator)
        .attr("fill", "none")
        .attr("stroke", "blue")
        .attr("stroke-width", 1);
};

//not solved - TODO : Do later - linkRadial
const convertLinksVerticalRadial = (svgRef, type) => {

    const svg = d3.select(svgRef.current);

    const nodeData = [
        { id: "D3", position: [2, 0], parentPosition: [2, 0] },
        { id: "Shapes", position: [1, 1], parentPosition: [2, 0] },
        { id: "Scales", position: [3, 1], parentPosition: [2, 0] },
        { id: "Links", position: [0, 2], parentPosition: [1, 1] },
        { id: "Areas", position: [1, 2], parentPosition: [1, 1] },
        { id: "Arcs", position: [2, 2], parentPosition: [1, 1] },
        { id: "Ordinal", position: [3, 2], parentPosition: [3, 1] },
        { id: "Quantize", position: [4, 2], parentPosition: [3, 1] }
    ];

    let linkGenerator;

    let xScale;
    let yScale;


    if (type === "vertical") {

        xScale = d3.scaleLinear().domain([0, 4]).range([25, 260]);
        yScale = d3.scaleLinear().domain([0, 2]).range([25, 260]);

        // Create a link generator for vertical links
        linkGenerator = d3.linkVertical()
            .source(d => d.position)
            .target(d => d.parentPosition)
            .x(d => xScale(d[0]))
            .y(d => yScale(d[1]));
    } else if (type === "radial") {
        // Create a link generator for horizontal links
        xScale = d3.scaleLinear().domain([0, 4]).range([0, Math.PI * 2]);
        yScale = d3.scaleLinear().domain([0, 2]).range([0, 90]);
        console.log("radial")
        console.log({ xScale })
        console.log({ yScale })

        linkGenerator = d3.linkRadial()
            .source(d => d.position)
            .target(d => d.parentPosition)
            .angle(d => {
                // console.log("angle ",xScale(d[0]))
                return xScale(d[0])
            })
            .radius(d => {
                // console.log("radius ",yScale(d[1]))
                return yScale(d[1])
            });
    }

    svg.selectAll("path")
        .data(nodeData)
        .join("path")
        .attr("d", linkGenerator)
        .attr("fill", "none")
        .attr("stroke", "blue")
        .attr("stroke-width", 1);
};

const linkVerticalCanvas = (canvasRefVertical) => {
    const canvas = canvasRefVertical.current;
    const context = canvas.getContext("2d");

    // Create a link generator for vertical links
    const linkGenerator = d3.linkVertical()
        .source(d => d.source)
        .target(d => d.target);

    const multiLinkData = [
        { source: [150, 25], target: [50, 100] },
        { source: [150, 25], target: [250, 100] },
    ];

    // Clear the canvas
    context.clearRect(0, 0, canvas.width, canvas.height);

    // Draw the links
    context.strokeStyle = "blue";
    context.lineWidth = 1;
    context.beginPath();
    multiLinkData.forEach(d => {
        const linkPath = linkGenerator(d);
        const path = new Path2D(linkPath);
        context.stroke(path);
    });
};



const E8Links = () => {
    const svgRefVertical = useRef(null);
    const svgRefHorizontal = useRef(null);
    const svgRefRadial = useRef(null);
    const svgRefSourceAndTarget = useRef(null);
    const svgRefLinkPositionScaleVertical = useRef(null);
    const svgRefLinkPositionScaleHorizontal = useRef(null);
    const svgRefConvertVertical = useRef(null);
    const svgRefConvertHorizontal = useRef(null);
    const svgRefConvertLinksVerticalToRadialVertical = useRef(null);
    const svgRefConvertLinksVerticalToRadialRadial = useRef(null);
    const canvasRefVertical = useRef(null);

    useEffect(() => {
        linkVertical(svgRefVertical);
        linkHorizontal(svgRefHorizontal);
        linkRadial(svgRefRadial);
        linkSourceAndTarget(svgRefSourceAndTarget);
        linkPositionScaleVertical(svgRefLinkPositionScaleVertical);
        linkPositionScaleHorizontal(svgRefLinkPositionScaleHorizontal)
        convertLinksVerticalHorizontal(svgRefConvertVertical, "vertical")
        convertLinksVerticalHorizontal(svgRefConvertHorizontal, "horizontal")
        convertLinksVerticalRadial(svgRefConvertLinksVerticalToRadialVertical, "vertical");
        convertLinksVerticalRadial(svgRefConvertLinksVerticalToRadialRadial, "radial");
        linkVerticalCanvas(canvasRefVertical);
    }, []);

    return (
        <div>
            <h5>Example 01 - Vertical Link</h5>
            <svg
                ref={svgRefVertical}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            />
            <hr />
            <h5>Example 02 - Horizontal Link</h5>
            <svg
                ref={svgRefHorizontal}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            />
            <hr />
            <h5>Example 03 - Radial Link</h5>
            <svg
                ref={svgRefRadial}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            />
            <hr />
            <h5>Example 04 - Link Source And Target</h5>
            <svg
                ref={svgRefSourceAndTarget}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            />
            <hr />
            <h5>Example 05 - Link Position Scale - vertical</h5>
            <svg
                ref={svgRefLinkPositionScaleVertical}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            />
            <hr />
            <h5>Example 06 - Link Position Scale - horizontal</h5>
            <svg
                ref={svgRefLinkPositionScaleHorizontal}
                width={"100%"}
                height={230}
                style={{ border: "1px dashed" }}
            />
            <hr />
            <h5>Example 07 - d3.linkVertical() to d3.linkHorizontal() </h5>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                <svg
                    ref={svgRefConvertVertical}
                    width={300}
                    height={250}
                    style={{ border: "1px dashed" }}
                />
                <svg
                    ref={svgRefConvertHorizontal}
                    width={300}
                    height={300}
                    style={{ border: "1px dashed" }}
                />

            </div>
            <hr />
            <h5>Example 08 - d3.linkVertical() to d3.linksRadial() </h5>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                <svg
                    ref={svgRefConvertLinksVerticalToRadialVertical}
                    width={300}
                    height={300}
                    style={{ border: "1px dashed" }}
                />
                <svg
                    ref={svgRefConvertLinksVerticalToRadialRadial}
                    width={300}
                    height={300}
                    style={{ border: "1px dashed" }}
                />
            </div>
            <hr />
            <h5>Example 09 - Vertical Link Canvas</h5>
            <canvas
                ref={canvasRefVertical}
                width={300}
                height={300}
                style={{ border: "1px dashed" }}
            />
        </div>
    );
};

export default E8Links;
