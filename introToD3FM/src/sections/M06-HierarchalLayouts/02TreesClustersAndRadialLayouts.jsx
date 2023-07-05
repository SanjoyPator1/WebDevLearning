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

const E2TreesClustersAndRadialLayouts = () => {
    const svgRefVertical = useRef(null);

    useEffect(() => {
        linkVertical(svgRefVertical);
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
            
        </div>
    );
};

export default E2TreesClustersAndRadialLayouts;
