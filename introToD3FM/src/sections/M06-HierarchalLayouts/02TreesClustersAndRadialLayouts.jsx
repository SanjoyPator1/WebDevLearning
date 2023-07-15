import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../components/styles";

const hierarchalModels = () => {
    const data = {
        name: "A",
        size: 1,
        children: [
            { name: "B", size: 2 },
            {
                name: "C",
                size: 3,
                children: [
                    { name: "E", size: 5 },
                    { name: "F", size: 6 },
                ],
            },
            { name: "D", size: 4 },
        ],
    };

    const root = d3.hierarchy(data);
    console.log({ root })

    //Node Properties
    console.log("node.data ", root.data)
    console.log("node.parent  ", root.parent)
    console.log("node.children  ", root.children)
    console.log("node.depth  ", root.depth)
    console.log("node.height  ", root.height)
    console.log("node.value   ", root.value) // optional - used by sum() and count()

    //Associated Links and Related Nodes
    console.log("node.links() ", root.links())
    console.log("node.ancestors() ", root.ancestors())
    const target_node = root.children[1].children[1]
    console.log("target_node ", target_node)
    console.log("node.path(target_node) ", root.path(target_node)) //shortest path
    console.log("node.descendants() ", root.descendants())
    console.log("node.leaves() ", root.leaves())

    //Copy
    console.log("node.copy() ", root.copy())

    //Applying a Function to Each Node in a Subtree
    root.each((node) => console.log("inside node.each(function) ", node.data.name))
    root.eachAfter((node) => console.log("inside node.eachAfter(function) ", node.data.name))
    root.eachBefore((node) => console.log("inside node.eachBefore(function)  ", node.data.name))

    // Setting the Value Property
    root.sum((d) => d.size);
    console.log("sum ", root.value);

    //count
    root.count();
    console.log("count ", root.value);

    //sorting
    //TODO

};

const treeLayout = (svgRefVertical) => {

    const data = {
        name: "A",
        size: 1,
        children: [
            { name: "B", size: 2 },
            {
                name: "C",
                size: 3,
                children: [
                    { name: "E", size: 5 },
                    { name: "F", size: 6 },
                ],
            },
            { name: "D", size: 4 },
        ],
    };

    const root = d3.hierarchy(data)
        .sort((a, b) => b.height - a.height || a.data.name.localeCompare(b.data.name));

    const treeLayout = d3.tree()
        .size([600, 160]);

    treeLayout(root)
    // console.log({ root })

    // console.log("root.links() ", root.links())
    // console.log("root.descendants() ", root.descendants())

    const svg = d3.select(svgRefVertical.current);

    // Draw the links
    svg
        .select('g.links')
        .selectAll('line.link')
        .data(root.links())
        .enter()
        .append('line')
        .attr('x1', (d) => { return d.source.x; })
        .attr('y1', (d) => { return d.source.y; })
        .attr('x2', (d) => { return d.target.x; })
        .attr('y2', (d) => { return d.target.y; })
        .attr('stroke', "darkgray")
        .attr('stroke-width', 2);

    svg.select('g.nodes')
        .selectAll('circle.node')
        .data(root.descendants())
        .enter()
        .append('circle')
        .attr('cx', (d) => { return d.x; })
        .attr('cy', (d) => { return d.y; })
        .attr('r', 10)
        .attr("fill", "lightblue")
        .attr('stroke', "darkgray")
        .attr('stroke-width', 1);
};

const treeNodeSizeAndPosition = (svgRef) => {

    // Define the input data for the tree
    const data = {
        name: "A",
        size: 1,
        children: [
            { name: "B", size: 2 },
            {
                name: "C",
                size: 3,
                children: [
                    { name: "E", size: 5 },
                    { name: "F", size: 6 },
                ],
            },
            { name: "D", size: 4 },
        ],
    };

    // Create the root of the tree hierarchy
    const root = d3.hierarchy(data)
        .sort((a, b) => b.height - a.height || a.data.name.localeCompare(b.data.name));

    // Create the tree layout and configure its properties
    const treeLayout = d3.tree()
        .nodeSize([30, 40])
        .separation((a, b) => (a.depth > b.depth) ? a.depth : b.depth);

    // Generate the tree layout by applying it to the root
    treeLayout(root);
    // console.log({ root });

    // Log the links and descendants of the root for debugging
    // console.log("root.links() ", root.links());
    // console.log("root.descendants() ", root.descendants());

    // Select the SVG element using the provided ref
    const svg = d3.select(svgRef.current);

    // Define the amount of horizontal shifting
    const xOffset = 200; // Adjust the value of xOffset to control the shifting

    // Draw the links
    svg.select("g.links")
        .selectAll("line.link")
        .data(root.links())
        .enter()
        .append("line")
        .attr("x1", (d) => d.source.x + xOffset)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x + xOffset)
        .attr("y2", (d) => d.target.y)
        .attr("stroke", "darkgray")
        .attr("stroke-width", 2);

    // Draw the nodes as circles
    svg.select("g.nodes")
        .selectAll("circle.node")
        .data(root.descendants())
        .enter()
        .append("circle")
        .attr("cx", (d) => d.x + xOffset)
        .attr("cy", (d) => d.y)
        .attr("r", 10)
        .attr("fill", "lightblue")
        .attr("stroke", "darkgray")
        .attr("stroke-width", 1);
}

const clusterLayout = (svgRef) => {

    const data = {
        name: "A",
        size: 1,
        children: [
            { name: "B", size: 2 },
            {
                name: "C",
                size: 3,
                children: [
                    { name: "E", size: 5 },
                    { name: "F", size: 6 },
                ],
            },
            { name: "D", size: 4 },
        ],
    };

    const root = d3.hierarchy(data).sort(
        (a, b) => b.height - a.height || a.data.name.localeCompare(b.data.name)
    );

    const clusterLayout = d3.cluster().size([400, 160]);

    clusterLayout(root);
    // console.log({ root });

    // console.log("root.links() ", root.links());
    // console.log("root.descendants() ", root.descendants());

    const svg = d3.select(svgRef.current);

    // Draw the links
    svg
        .select("g.links")
        .selectAll("line.link")
        .data(root.links())
        .enter()
        .append("line")
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y)
        .attr("stroke", "darkgray")
        .attr("stroke-width", 2);

    // Draw the nodes as circles
    svg
        .select("g.nodes")
        .selectAll("circle.node")
        .data(root.descendants())
        .enter()
        .append("circle")
        .attr("cx", (d) => d.x)
        .attr("cy", (d) => d.y)
        .attr("r", 10)
        .attr("fill", "lightblue")
        .attr("stroke", "darkgray")
        .attr("stroke-width", 1);
}

const clusterLayoutNodeSizeAndPosition = (svgRef) => {

    const data = {
        name: "A",
        size: 1,
        children: [
            { name: "B", size: 2 },
            {
                name: "C",
                size: 3,
                children: [
                    { name: "E", size: 5 },
                    { name: "F", size: 6 },
                ],
            },
            { name: "D", size: 4 },
        ],
    };

    const root = d3.hierarchy(data).sort(
        (a, b) => b.height - a.height || a.data.name.localeCompare(b.data.name)
    );

    const clusterLayout = d3.cluster()
        .nodeSize([30, 40])
        .separation((a, b) => a.depth);;

    clusterLayout(root);
    // console.log({ root });

    // console.log("root.links() ", root.links());
    // console.log("root.descendants() ", root.descendants());

    const svg = d3.select(svgRef.current);

    // Define the amount of horizontal shifting
    const xOffset = 200; // Adjust the value of xOffset to control the shifting

    // Draw the links
    svg
        .select("g.links")
        .selectAll("line.link")
        .data(root.links())
        .enter()
        .append("line")
        .attr("x1", (d) => d.source.x + xOffset)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x + xOffset)
        .attr("y2", (d) => d.target.y)
        .attr("stroke", "darkgray")
        .attr("stroke-width", 2);

    // Draw the nodes as circles
    svg
        .select("g.nodes")
        .selectAll("circle.node")
        .data(root.descendants())
        .enter()
        .append("circle")
        .attr("cx", (d) => d.x + xOffset)
        .attr("cy", (d) => d.y)
        .attr("r", 10)
        .attr("fill", "lightblue")
        .attr("stroke", "darkgray")
        .attr("stroke-width", 1);
}

const treeRadialSizeAndPosition = (svgRef) => {
    const data = {
        name: "A",
        size: 1,
        children: [
            { name: "B", size: 2 },
            {
                name: "C",
                size: 3,
                children: [
                    { name: "E", size: 5 },
                    { name: "F", size: 6 },
                ],
            },
            { name: "D", size: 4 },
        ],
    };

    const root = d3.hierarchy(data).sort(
        (a, b) => b.height - a.height || a.data.name.localeCompare(b.data.name)
    );

    const radialLayout = d3.cluster().size([360, 150]);

    radialLayout(root);
    console.log({ root });

    console.log("root.links() ", root.links());
    console.log("root.descendants() ", root.descendants());

    const svg = d3.select(svgRef.current);

    // Draw the links as radial lines
    const lineGen = d3.lineRadial()
        .angle((d) => (d.x * Math.PI) / 180)
        .radius((d) => d.y);

    svg
        .select("g.links")
        .selectAll("path.link")
        .data(root.links())
        .enter()
        .append("path")
        .attr("d", (d) => lineGen([d.source, d.target]))
        .attr("stroke", "darkgray")
        .attr("stroke-width", 2)
        .attr("fill", "none");

    // Draw the nodes as circles with size proportional to their data size
    svg
        .select("g.nodes")
        .selectAll("circle.node")
        .data(root.descendants())
        .enter()
        .append("circle")
        .attr("cx", 0)
        .attr("cy", (d) => -d.y)
        .attr("r", 10)
        .attr("transform", (d) => `rotate(${d.x}, 0, 0)`)
        .attr("fill", "lightblue")
        .attr("stroke", "darkgray")
        .attr("stroke-width", 1);
};

//Graph layout
const graphLayoutHorizontal = (svgRef) => {

    // Define the input data for the graph
    const graphData = {
        id: "patientEntryId",
        name: "patient entry",
        type: "startEvent",
        children: [
          {
            id: "humanTaskId",
            name: "human task",
            type: "userTask",
            children: [
              {
                id: "covidAssessmentId",
                name: "covid assessment",
                type: "businessRuleTask",
                children: [
                  {
                    id: "desicionGatewayId",
                    name: "decision gateway",
                    type: "exclusiveGateway",
                    children: [
                      {
                        id: "toBeDetainedId",
                        name: "to be detained",
                        type: "serviceTask",
                        children: [
                          {
                            id: "patientExitId",
                            name: "patient exit",
                            type: "endEvent"
                          }
                        ]
                      },
                      {
                        id: "notToBeDetainedId",
                        name: "not to be detained",
                        type: "serviceTask",
                        children: [
                          {
                            id: "patientExitId",
                            name: "patient exit",
                            type: "endEvent"
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      };
      

    // Create the root of the tree hierarchy
    const root = d3.hierarchy(graphData)
        .sort((a, b) => b.height - a.height || a.data.name.localeCompare(b.data.name));

    // Create the tree layout and configure its properties
    const treeLayout = d3.tree()
        .nodeSize([40, 80])
        .separation((a,b) => a.depth);

    // Generate the tree layout by applying it to the root
    treeLayout(root);
    // console.log({ root });

    // Log the links and descendants of the root for debugging
    // console.log("root.links() ", root.links());
    // console.log("root.descendants() ", root.descendants());

    // Select the SVG element using the provided ref
    const svg = d3.select(svgRef.current);

    // Define the amount of horizontal shifting
    const xOffset = 200; // Adjust the value of xOffset to control the shifting
    const yOffset = 200; // Adjust the value of xOffset to control the shifting

    // Draw the links
    svg.select("g.links")
        .selectAll("line.link")
        .data(root.links())
        .enter()
        .append("line")
        .attr("x1", (d) => d.source.y + yOffset)
        .attr("y1", (d) => d.source.x + xOffset)
        .attr("x2", (d) => d.target.y + yOffset)
        .attr("y2", (d) => d.target.x + xOffset)
        .attr("stroke", "darkgray")
        .attr("stroke-width", 2);

    // Draw the nodes as circles
    svg.select("g.nodes")
        .selectAll("circle.node")
        .data(root.descendants())
        .enter()
        .append("circle")
        .attr("cx", (d) => d.y + yOffset)
        .attr("cy", (d) => d.x + xOffset)
        .attr("r", 20)
        .attr("fill", "lightblue")
        .attr("stroke", "darkgray")
        .attr("stroke-width", 1);
}

const familyTree = (svgRef) => {

    const data = [
    {
        id: "patientEntryId",
        label: "patient entry",
        type: "startEvent",
        children: [
            {
                id: "humanTaskId",
                label: "human task",
                type: "userTask",
                children: [
                    {
                        id: "covidAssessmentId",
                        label: "covid assessment",
                        type: "businessRuleTask",
                        children: [
                            {
                                id: "desicionGatewayId",
                                label: "desicion gateway",
                                type: "exclusiveGateway",
                                children: [
                                    {
                                        id: "toBeDetainedId",
                                        label: "to be detained",
                                        type: "serviceTask",
                                        children: [
                                            {
                                                id: "patientExitId",
                                                label: "patient exit",
                                                type: "endEvent"
                                            }
                                        ]
                                    },
                                    {
                                        id: "notToBeDetainedId",
                                        label: "not to be detained",
                                        type: "serviceTask",
                                        children: [
                                            {
                                                id: "patientExitId",
                                                label: "patient exit",
                                                type: "endEvent"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
]


    const svg = d3.select(svgRef.current);
    const width = svg.attr('width');
    const height = svg.attr('height');

    const margin = { top: 10, right: 50, bottom: 10, left: 150 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const treeLayout = d3.tree().size([innerHeight, innerWidth]);

    const zoomG = svg
      .attr('width', width)
      .attr('height', height)
      .append('g');

    const g = zoomG.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const linkPathGenerator = d3.linkHorizontal().x(d => d.y).y(d => d.x);

    const root = d3.hierarchy(data);

    const update = (source) => {
      const treeData = treeLayout(root);

      const links = treeData.links();
      const nodes = treeData.descendants();

      g.selectAll('path.link')
        .data(links)
        .enter()
        .append('path')
        .attr('d', linkPathGenerator)
        .attr('class', 'link')
        .attr('fill', 'none')
        .attr('stroke', 'darkgray')
        .attr('stroke-width', 1);

      const nodeEnter = g
        .selectAll('g.node')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${source.y0},${source.x0})`);

      nodeEnter
        .append('circle')
        .attr('r', 10)
        .attr('fill', 'lightblue')
        .attr('stroke', 'darkgray')
        .attr('stroke-width', 1);

      nodeEnter
        .append('text')
        .attr('x', d => (d.children ? -13 : 13))
        .attr('text-anchor', d => (d.children ? 'end' : 'start'))
        .attr('dy', '0.32em')
        .text(d => d.data.name);

      const nodeUpdate = nodeEnter.merge(nodeEnter);

      nodeUpdate
        .transition()
        .duration(750)
        .attr('transform', d => `translate(${d.y},${d.x})`);

      nodeUpdate.select('circle').attr('fill-opacity', 1).attr('stroke-opacity', 1);

      const nodeExit = nodeEnter.exit().remove();

      treeData.each(d => {
        d.x0 = d.x;
        d.y0 = d.y;
      });
    };

    update(root);
}


const E2TreesClustersAndRadialLayouts = () => {
    const svgRefTreeLayout = useRef(null);
    const svgRefTreeNodeSizeAndPosition = useRef(null);
    const svgRefClusterLayout = useRef(null);
    const svgRefClusterNodeSizeAndPosition = useRef(null);
    const svgRefRadialLayouts = useRef(null);
    const svgRefGraphLayoutHorizontal= useRef(null);
    const svgRefFamilyTree= useRef(null);
    

    useEffect(() => {
        // hierarchalModels();
        treeLayout(svgRefTreeLayout);
        treeNodeSizeAndPosition(svgRefTreeNodeSizeAndPosition);
        clusterLayout(svgRefClusterLayout)
        clusterLayoutNodeSizeAndPosition(svgRefClusterNodeSizeAndPosition)
        treeRadialSizeAndPosition(svgRefRadialLayouts)
        graphLayoutHorizontal(svgRefGraphLayoutHorizontal)
        familyTree(svgRefFamilyTree)
    }, []);

    return (
        <div>
            <h5>Example 01 - Tree Layout</h5>
            <svg
                ref={svgRefTreeLayout}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            >
                <g transform="translate(0,10)">
                    <g class="links"></g>
                    <g class="nodes"></g>
                </g>
            </svg>
            <hr />
            <h5>Example 02 - Tree Layout with tree node size and position</h5>
            <svg
                ref={svgRefTreeNodeSizeAndPosition}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            >
                <g transform="translate(0,10)">
                    <g class="links"></g>
                    <g class="nodes"></g>
                </g>
            </svg>
            <hr />
            <h5>Example 03 - cluster Layout with tree size</h5>
            <svg
                ref={svgRefClusterLayout}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            >
                <g transform="translate(0,10)">
                    <g class="links"></g>
                    <g class="nodes"></g>
                </g>
            </svg>
            <hr />
            <h5>Example 04 - cluster Layout with tree node size and position</h5>
            <svg
                ref={svgRefClusterNodeSizeAndPosition}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            >
                <g transform="translate(0,10)">
                    <g class="links"></g>
                    <g class="nodes"></g>
                </g>
            </svg>
            <hr />
            <h5>Example 05 - Radial Layout with tree node size and position</h5>
            <svg
                ref={svgRefRadialLayouts}
                width={"100%"}
                height={200}
                style={{ border: "1px dashed" }}
            >
                <g transform="translate(0,10)">
                    <g class="links"></g>
                    <g class="nodes"></g>
                </g>
            </svg>
            <hr />
            <h5>Example 06 - Graph Layout Horizontal with tree node size and position</h5>
            <svg
                ref={svgRefGraphLayoutHorizontal}
                width={"100%"}
                height={500}
                style={{ border: "1px dashed" }}
            >
                <g transform="translate(0,10)">
                    <g class="links"></g>
                    <g class="nodes"></g>
                </g>
            </svg>
            <hr />
            <h5>Example 07 - Family tree with tree node size and position</h5>
            <svg
                ref={svgRefFamilyTree}
                width={"100%"}
                height={500}
                style={{ border: "1px dashed" }}
            >
                <g transform="translate(0,10)">
                    <g class="links"></g>
                    <g class="nodes"></g>
                </g>
            </svg>
            <hr />
        </div>
    );
};

export default E2TreesClustersAndRadialLayouts;
